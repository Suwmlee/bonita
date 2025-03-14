import os
import logging
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse
from celery import shared_task, group
from celery.result import allow_join_result

from multiprocessing import Semaphore

from bonita import schemas
from bonita.core.config import settings
from bonita.db import SessionFactory
from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.metadata import Metadata
from bonita.db.models.record import TransRecords
from bonita.db.models.scraping import ScrapingConfig
from bonita.db.models.setting import SystemSetting
from bonita.db.models.watch_history import WatchHistory
from bonita.modules.scraping.number_parser import FileNumInfo
from bonita.modules.scraping.scraping import add_mark, process_nfo_file, process_cover, scraping, load_all_NFO_from_folder
from bonita.utils.fileinfo import BasicFileInfo, TargetFileInfo
from bonita.modules.transfer.transfer import transSingleFile, transferfile, findAllVideos
from bonita.utils.downloader import process_cached_file, update_cache_from_local
from bonita.utils.filehelper import cleanExtraMedia, cleanFolderWithoutSuffix, video_type
from bonita.utils.http import get_active_proxy
from bonita.modules.media_service.emby_service import EmbyService
from bonita.modules.media_service.jellyfin_service import JellyfinService
from bonita.modules.media_service.trakt_service import TraktService
from bonita.db.models.media_item import MediaItem


# 创建信号量，最多允许X任务同时执行
max_concurrent_tasks = settings.MAX_CONCURRENT_TASKS
semaphore = Semaphore(max_concurrent_tasks)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:all')
def celery_transfer_entry(self, task_json):
    """ 转移任务入口
    """
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "transfer task: start"})
    task_info = schemas.TransferConfigPublic(**task_json)
    logger.info(f"transfer task {task_info.id}: start")
    # 获取 source 文件夹下所有顶层文件/文件夹
    dirs = os.listdir(task_info.source_folder)

    # 创建转移任务组
    transfer_group = group(celery_transfer_group.s(task_json, os.path.join(
        task_info.source_folder, single_folder)) for single_folder in dirs)

    # 先执行所有转移任务
    transfer_result = transfer_group.apply_async()

    # 使用 allow_join_result 上下文管理器等待转移任务完成
    with allow_join_result():
        done_list = transfer_result.get()
        if isinstance(done_list, list):
            flat_done_list = []
            for sublist in done_list:
                if isinstance(sublist, list):
                    flat_done_list.extend(sublist)
                else:
                    flat_done_list.append(sublist)
            done_list = flat_done_list
        # 剔除 done_list 中的重复项
        if done_list:
            done_list = list(set(done_list))
        logger.info(f"Transfer task {task_info.id} completed with {len(done_list)} files transferred")

        # 转移完成后，判断是否执行清理任务或扫描任务
        if task_info.clean_others:
            celery_clean_others.apply_async(args=[task_info.output_folder, done_list])
        if task_info.auto_watch:
            celery_emby_scan.apply_async(args=[task_json])

    return True


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:group')
def celery_transfer_group(self, task_json, full_path, isEntry=False):
    """ 对 group/folder 内所有关联文件进行转移
    """
    with semaphore:
        self.update_state(state="PROGRESS", meta={"progress": 0, "step": "celery_transfer_pool: start"})
        logger.info(f"transfer group start {full_path}")
        if not os.path.exists(full_path):
            logger.info(f"[!] Transfer not found {full_path}")
            return []
        task_info = schemas.TransferConfigPublic(**task_json)
        is_series = False
        if task_info.content_type == 2:
            is_series = True

        if os.path.isdir(full_path):
            waiting_list = findAllVideos(full_path, task_info.source_folder, re.split("[,，]", task_info.escape_folder))
        else:
            if not os.path.splitext(full_path)[1].lower() in video_type:
                logger.info(f"[!] Transfer failed {full_path}")
                return []
            waiting_list = []
            tf = BasicFileInfo(full_path)
            tf.set_root_folder(task_info.source_folder)
            waiting_list.append(tf)

        logger.info(f"[+] Transfer check {full_path}")
        try:
            session = SessionFactory()
            done_list = []
            for original_file in waiting_list:
                if not isinstance(original_file, BasicFileInfo):
                    continue
                record = session.query(TransRecords).filter(TransRecords.srcpath == original_file.full_path).first()
                if not record:
                    record = TransRecords()
                    record.srcname = original_file.filename
                    record.srcpath = original_file.full_path
                    record.srcfolder = original_file.parent_folder
                    record.create(session)
                if record.srcdeleted:
                    record.srcdeleted = False
                if record.ignored:
                    logger.info(f"[-] ignore {original_file.full_path}")
                    continue
                record.task_id = task_info.id
                if task_info.sc_enabled:
                    logger.info(f"[-] need scraping")
                    scraping_conf = session.query(ScrapingConfig).filter(ScrapingConfig.id == task_info.sc_id).first()
                    if not scraping_conf:
                        logger.info(f"[-] scraping config not found")
                        continue
                    scraping_task = celery_scrapping.apply(args=[original_file.full_path, scraping_conf.to_dict()])
                    with allow_join_result():
                        metabase_json = scraping_task.get()
                    if not metabase_json:
                        record.updatetime = datetime.now()
                        logger.error(f"[-] scraping failed {original_file.full_path}")
                        continue
                    metamixed = schemas.MetadataMixed.model_validate(metabase_json)

                    output_folder = os.path.abspath(os.path.join(task_info.output_folder, metamixed.extra_folder))
                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)
                    # 写入NFO文件
                    process_nfo_file(output_folder, metamixed.extra_filename, metamixed.__dict__)
                    cache_cover_filepath = process_cached_file(session, metamixed.cover, metamixed.number)
                    pics = process_cover(cache_cover_filepath, output_folder, metamixed.extra_filename)
                    if scraping_conf.watermark_enabled:
                        add_mark(pics, metamixed.tag, scraping_conf.watermark_location, scraping_conf.watermark_size)
                    # 移动
                    destpath = transSingleFile(original_file, output_folder,
                                               metamixed.extra_filename, task_info.operation)
                    done_list.append(destpath)
                    if record.destpath != destpath:
                        # 如果新的路径和之前不同，则删除之前的文件
                        if os.path.exists(record.destpath):
                            os.remove(record.destpath)
                    # 更新
                    record.destpath = destpath
                    record.deleted = False
                    record.updatetime = datetime.now()
                    logger.info(f"[-] scraping transfer end")
                else:
                    logger.info(f"[-] start transfer")
                    target_file = TargetFileInfo(task_info.output_folder)
                    if record.top_folder:
                        target_file.force_update_top_folder(record.top_folder)
                    # 如果 record 中定义了剧集信息，则使用 record 中的信息
                    if record.isepisode:
                        target_file.force_update_episode(record.isepisode, record.season, record.episode)
                    # 开始转移
                    target_file = transferfile(original_file, target_file,
                                               optimize_name_tag=task_info.optimize_name, series_tag=is_series,
                                               file_list=waiting_list, linktype=task_info.operation)
                    done_list.append(target_file.full_path)
                    if record.destpath != target_file.full_path:
                        # 如果新的路径和之前不同，则删除之前的文件
                        if os.path.exists(record.destpath):
                            os.remove(record.destpath)
                    # 更新
                    record.isepisode = target_file.is_episode
                    record.season = target_file.season_number
                    record.episode = target_file.episode_number
                    record.top_folder = target_file.top_folder
                    record.second_folder = target_file.second_folder
                    record.destpath = target_file.full_path
                    record.deleted = False
                    record.updatetime = datetime.now()
                    logger.info(f"[-] transfer end")
        except Exception as e:
            logger.error(e)
        finally:
            session.commit()
            session.close()

        if isEntry and task_info.auto_watch:
            try:
                logger.info(f"[+] group task: start emby scan")
                celery_emby_scan.apply(args=[task_json])
            except Exception as e:
                logger.error(f"[!] group task: emby scan failed")
                logger.error(e)

        logger.info(f"transfer group end {full_path}")
        return done_list


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='scraping:single')
def celery_scrapping(self, file_path, scraping_dict):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "scraping task: start"})
    logger.info(f"[+] scraping task: start")
    try:
        session = SessionFactory()
        scraping_conf = schemas.ScrapingConfigPublic(**scraping_dict)
        # 根据路径获取额外自定义信息
        fileNumInfo = FileNumInfo(file_path)
        extrainfo = session.query(ExtraInfo).filter(ExtraInfo.filepath == file_path).first()
        if not extrainfo:
            extrainfo = ExtraInfo(filepath=file_path)
            extrainfo.number = fileNumInfo.num
            extrainfo.partNumber = int(fileNumInfo.part.replace("-CD", "")) if fileNumInfo.part else 0
            extrainfo.tag = ', '.join(map(str, fileNumInfo.tags()))
            extrainfo.create(session)
        # 处理指定源/强制从网站更新
        metadata_record = None
        if extrainfo.specifiedurl:
            metadata_record = session.query(Metadata).filter(
                Metadata.number == extrainfo.number,
                Metadata.detailurl == extrainfo.specifiedurl).order_by(Metadata.id.desc()).first()
        elif extrainfo.specifiedsource:
            metadata_record = session.query(Metadata).filter(
                Metadata.number == extrainfo.number,
                Metadata.site == extrainfo.specifiedsource).order_by(Metadata.id.desc()).first()
        if not metadata_record:
            metadata_record = session.query(Metadata).filter(
                Metadata.number == extrainfo.number).order_by(Metadata.id.desc()).first()
        if metadata_record:
            logger.info(f"[-] find existing metadata: {metadata_record.number}")
            metadata_mixed = schemas.MetadataMixed(**metadata_record.to_dict())
        else:
            # 如果没有找到任何记录，则从网络抓取
            proxy = get_active_proxy(session)
            json_data = scraping(extrainfo.number,
                                 scraping_conf.scraping_sites,
                                 extrainfo.specifiedsource,
                                 extrainfo.specifiedurl,
                                 proxy
                                 )
            # Return if blank dict returned (data not found)
            if not json_data or json_data.get('title') == '':
                logger.error(f"[-] scraping failed {file_path}")
                return None
            # 数据转换
            metadata_base = schemas.MetadataBase(**json_data)
            filter_dict = Metadata.filter_dict(Metadata, metadata_base.__dict__)
            metadata_record = Metadata(**filter_dict)
            if scraping_conf.save_metadata:
                metadata_record.create(session)
            metadata_mixed = schemas.MetadataMixed(**metadata_record.to_dict())

        # 根据规则生成文件夹和文件名
        maxlen = scraping_conf.max_title_len
        extra_folder = eval(scraping_conf.location_rule, metadata_mixed.__dict__)
        extra_name = eval(scraping_conf.naming_rule, metadata_mixed.__dict__)
        if 'actor' in scraping_conf.location_rule and len(metadata_mixed.actor) > maxlen:
            extra_folder = eval(scraping_conf.location_rule.replace("actor", "'多人作品'"), metadata_mixed.__dict__)
            extra_name = eval(scraping_conf.naming_rule.replace("actor", "'多人作品'"), metadata_mixed.__dict__)
        if 'title' in scraping_conf.location_rule and len(metadata_mixed.title) > maxlen:
            shorttitle = metadata_mixed.title[0:maxlen]
            extra_folder = extra_folder.replace(metadata_mixed.title, shorttitle)
            extra_name = extra_name.replace(metadata_mixed.title, shorttitle)
        metadata_mixed.extra_folder = extra_folder
        metadata_mixed.extra_filename = extra_name

        # 将 extrainfo.tag 中的标签添加到 metadata_base.tag 中，过滤重复的标签
        existing_tags = set(metadata_mixed.tag.split(", "))
        new_tags = set(extrainfo.tag.split(", "))
        combined_tags = existing_tags.union(new_tags)
        metadata_mixed.tag = ", ".join(combined_tags)
        # 更新文件名称，part -C -CD1
        if extrainfo.partNumber:
            metadata_mixed.extra_filename += f"-CD{extrainfo.partNumber}"
            metadata_mixed.extra_part = extrainfo.partNumber

        return metadata_mixed
    except Exception as e:
        logger.error(e)
    finally:
        session.commit()
        session.close()
    return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='clean:clean_others')
def celery_clean_others(self, folder_path, done_list):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "clean others: start"})
    logger.info(f"[+] clean others task for {folder_path}: start")

    cleaned_files = []
    dest_list = findAllVideos(folder_path, '', [], 2)
    for dest in dest_list:
        if dest not in done_list:
            cleaned_files.append(dest)
    for torm in cleaned_files:
        logger.info(f"[!] remove other file: [{torm}]")
        os.remove(torm)
        cleanExtraMedia(folder_path)
        cleanFolderWithoutSuffix(folder_path, video_type)

    logger.info(f"Clean others completed. Removed {len(cleaned_files)} files")
    return cleaned_files


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='emby:scan')
def celery_emby_scan(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "emby scan: start"})
    logger.info(f"[+] emby scan: start")
    try:
        # Get Emby configuration from the database
        session = SessionFactory()
        try:
            emby_host = session.query(SystemSetting).filter(SystemSetting.key == "emby_host").first()
            emby_apikey = session.query(SystemSetting).filter(SystemSetting.key == "emby_apikey").first()

            if not emby_host or not emby_apikey:
                logger.error("Emby host or API key not configured")
                return

            # Extract the actual values from the SystemSetting objects
            emby_host_value = emby_host.value
            emby_apikey_value = emby_apikey.value
        finally:
            session.close()

        self.update_state(state="PROGRESS", meta={"progress": 50, "step": "emby scan: sending request"})

        # Use the EmbyService to trigger a library scan, passing the configuration
        EmbyService.trigger_library_scan(emby_host_value, emby_apikey_value)

        self.update_state(state="PROGRESS", meta={"progress": 100, "step": "emby scan: complete"})

    except Exception as e:
        logger.error(f"Error during Emby library scan: {str(e)}")
        return


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='import:nfo')
def celery_import_nfo(self, folder_path, option):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "import nfo: start"})
    logger.info(f"[+] import nfo: start")
    try:
        metadata_list = load_all_NFO_from_folder(folder_path)
        # 过滤有效的nfo信息
        title_to_metadata = {}
        for nfo_dict in metadata_list:
            title = nfo_dict['nfo'].get('title', '')
            if title:
                if title not in title_to_metadata:
                    title_to_metadata[title] = []
                title_to_metadata[title].append(nfo_dict)
        # 处理重复的title，保留一个有cover_path的
        filtered_metadata_list = []
        for title, nfo_dicts in title_to_metadata.items():
            if len(nfo_dicts) == 1:
                filtered_metadata_list.append(nfo_dicts[0])
            else:
                has_cover = [nfo_dict for nfo_dict in nfo_dicts if nfo_dict['cover_path']]
                if has_cover:
                    filtered_metadata_list.append(has_cover[0])
                else:
                    filtered_metadata_list.append(nfo_dicts[0])

        # 用过滤后的列表替换原始列表
        metadata_list = filtered_metadata_list
        logger.info(
            f"[+] import nfo: filtered {len(title_to_metadata)} titles from {len(filtered_metadata_list)} NFO files")
        for nfo_dict in metadata_list:
            nfo_data = nfo_dict['nfo']
            cover_path = nfo_dict['cover_path']
            try:
                metadata_base = schemas.MetadataBase(**nfo_data)
                # 如果 title 中包含 number，则删除 number
                if metadata_base.number in metadata_base.title:
                    metadata_base.title = metadata_base.title.replace(metadata_base.number, '').strip(' -')
            except Exception as e:
                logger.info(f"[!] convert nfo failed: {nfo_data}")
                logger.error(f"[!] convert nfo failed: {str(e)}")
                continue
            if metadata_base.site == "" and metadata_base.detailurl:
                # 从detailurl中提取域名作为site
                try:
                    parsed_url = urlparse(metadata_base.detailurl)
                    # 获取域名部分，去掉www.前缀
                    domain = parsed_url.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    # 提取主域名部分
                    parts = domain.split('.')
                    if len(parts) >= 2:
                        metadata_base.site = parts[-2]  # 取主域名部分
                    else:
                        metadata_base.site = domain
                except:
                    # 如果解析失败，直接使用完整URL
                    metadata_base.site = metadata_base.detailurl
            try:
                session = SessionFactory()
                metadata_record = session.query(Metadata).filter(
                    Metadata.number == metadata_base.number).order_by(Metadata.id.desc()).first()
                # 如果 metadata_record 存在，根据 option 决定是否更新
                if metadata_record:
                    if option == 'ignore':
                        # 忽略重复
                        continue
                    else:
                        # 强制更新
                        session.delete(metadata_record)
                # 从本地更新缓存图片
                if cover_path and os.path.exists(cover_path):
                    if not metadata_base.cover or metadata_base.cover == '':
                        metadata_base.cover = str(uuid.uuid4()).replace('-', '')
                    update_cache_from_local(session, cover_path, metadata_base.number, metadata_base.cover)
                filter_dict = Metadata.filter_dict(Metadata, metadata_base.__dict__)
                metadata_db = Metadata(**filter_dict)
                metadata_db.create(session)
            except Exception as e:
                logger.error(f"[!] import nfo {nfo_dict['nfo_path']} failed: {str(e)}")
                continue
            finally:
                session.close()
    except Exception as e:
        logger.error(f"[!] import nfo failed: {str(e)}")
    return True


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='watch_history:sync')
def celery_sync_watch_history(self, sources=None, days=30, limit=100):
    """Syncs watch history from multiple sources (Trakt, Emby, Jellyfin)
    
    Args:
        sources (list, optional): List of sources to sync from. If None, syncs from all configured sources.
        days (int, optional): Number of days of history to fetch. Defaults to 30.
        limit (int, optional): Maximum number of items to fetch per source. Defaults to 100.
    
    Returns:
        bool: True if sync was successful
    """
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "watch history sync: start"})
    logger.info(f"[+] watch history sync: start")
    
    if sources is None:
        sources = ["trakt", "emby", "jellyfin"]
    
    new_records = 0
    updated_records = 0
    
    session = SessionFactory()
    try:
        # Process each source
        for source_idx, source in enumerate(sources):
            progress_pct = int((source_idx / len(sources)) * 90)
            self.update_state(state="PROGRESS", meta={"progress": progress_pct, "step": f"watch history sync: processing {source}"})
            
            try:
                if source == "trakt":
                    trakt_records = sync_trakt_history(session, days, limit)
                    if trakt_records:
                        new_records += trakt_records[0]
                        updated_records += trakt_records[1]
                elif source == "emby":
                    emby_records = sync_emby_history(session, days, limit)
                    if emby_records:
                        new_records += emby_records[0]
                        updated_records += emby_records[1]
                elif source == "jellyfin":
                    jellyfin_records = sync_jellyfin_history(session, days, limit)
                    if jellyfin_records:
                        new_records += jellyfin_records[0]
                        updated_records += jellyfin_records[1]
            except Exception as e:
                logger.error(f"Error syncing from {source}: {str(e)}")
                # Continue with other sources even if one fails
        
        # Commit all changes
        session.commit()
        
        self.update_state(state="PROGRESS", meta={"progress": 100, "step": "watch history sync: complete"})
        logger.info(f"[+] Watch history sync complete. Added {new_records} new records, updated {updated_records} records")
        
    except Exception as e:
        logger.error(f"Error during watch history sync: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()
    
    return True


def sync_trakt_history(session, days=30, limit=100):
    """Syncs watch history from Trakt
    
    Args:
        session: Database session
        days (int): Number of days of history to fetch
        limit (int): Maximum number of items to fetch
    
    Returns:
        tuple: (new_records, updated_records)
    """
    try:
        # Get Trakt configuration
        trakt_client_id = session.query(SystemSetting).filter(SystemSetting.key == "trakt_client_id").first()
        trakt_access_token = session.query(SystemSetting).filter(SystemSetting.key == "trakt_access_token").first()
        
        if not trakt_client_id or not trakt_access_token:
            logger.info("Trakt client ID or access token not configured")
            return (0, 0)
            
        # Extract the actual values
        trakt_client_id_value = trakt_client_id.value
        trakt_access_token_value = trakt_access_token.value
        
        # Fetch watch history
        watch_history = TraktService.get_watch_history(
            trakt_client_id_value,
            trakt_access_token_value,
            days=days,
            limit=limit,
            extended=True
        )
        
        if not watch_history:
            logger.info("No watch history found on Trakt")
            return (0, 0)
            
        # Fetch ratings
        ratings = TraktService.get_ratings(trakt_client_id_value, trakt_access_token_value)
        
        # Process watch history
        new_records = 0
        updated_records = 0
        
        for item in watch_history:
            # Extract movie data
            movie = item.get("movie", {})
            ids = movie.get("ids", {})
            
            trakt_id = str(ids.get("trakt", ""))
            if not trakt_id:
                continue
                
            # Extract watch timestamp
            played_at = None
            if "watched_at" in item:
                played_at = datetime.fromisoformat(item["watched_at"].replace("Z", "+00:00"))
            
            # Extract movie metadata
            title = movie.get("title", "")
            year = movie.get("year")
            overview = movie.get("overview", "")
            genres = ", ".join(movie.get("genres", [])) if "genres" in movie else ""
            runtime = movie.get("runtime")
            
            # Get rating if available
            rating = ratings.get(trakt_id, 0.0)
            has_rating = rating > 0
            
            # 获取外部ID
            imdb_id = ids.get("imdb")
            tmdb_id = str(ids["tmdb"]) if "tmdb" in ids and ids["tmdb"] else None
            tvdb_id = str(ids["tvdb"]) if "tvdb" in ids and ids["tvdb"] else None
            
            # 查找或创建MediaItem
            media_item = None
            
            # 按外部ID查找
            if imdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.imdb_id == imdb_id).first()
            if not media_item and tmdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.tmdb_id == tmdb_id).first()
            if not media_item and tvdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.tvdb_id == tvdb_id).first()
                
            # 如果没找到，按标题和年份查找
            if not media_item:
                query = session.query(MediaItem).filter(MediaItem.title == title)
                if year:
                    query = query.filter(MediaItem.year == year)
                media_item = query.first()
                
            # 如果仍然没找到，创建新的MediaItem
            if not media_item:
                media_item = MediaItem(
                    media_type="movie",
                    title=title,
                    original_title=None,
                    year=year,
                    imdb_id=imdb_id,
                    tmdb_id=tmdb_id,
                    tvdb_id=tvdb_id
                )
                session.add(media_item)
                session.flush()  # 获取ID
            
            # 检查是否已存在观看记录
            existing_record = session.query(WatchHistory).filter(
                WatchHistory.source == "trakt",
                WatchHistory.external_id == trakt_id).first()
            
            # 创建或更新观看记录
            if existing_record:
                # 更新关联的MediaItem
                existing_record.media_item_id = media_item.id
                
                # 只有在新日期更晚时才更新played_at
                if played_at and (not existing_record.played_at or played_at > existing_record.played_at):
                    existing_record.played_at = played_at
                
                existing_record.rating = rating
                existing_record.has_rating = has_rating
                
                updated_records += 1
            else:
                # 创建新记录
                new_record = WatchHistory(
                    source="trakt",
                    external_id=trakt_id,
                    media_item_id=media_item.id,
                    played_at=played_at,
                    rating=rating,
                    has_rating=has_rating
                )
                session.add(new_record)
                new_records += 1
        
        return (new_records, updated_records)
        
    except Exception as e:
        logger.error(f"Error syncing from Trakt: {str(e)}")
        raise


def sync_emby_history(session, days=30, limit=100):
    """Syncs watch history from Emby
    
    Args:
        session: Database session
        days (int): Number of days of history to fetch
        limit (int): Maximum number of items to fetch
    
    Returns:
        tuple: (new_records, updated_records)
    """
    try:
        # Get Emby configuration
        emby_host = session.query(SystemSetting).filter(SystemSetting.key == "emby_host").first()
        emby_apikey = session.query(SystemSetting).filter(SystemSetting.key == "emby_apikey").first()
        
        if not emby_host or not emby_apikey:
            logger.info("Emby host or API key not configured")
            return (0, 0)
            
        # Extract the actual values
        emby_host_value = emby_host.value
        emby_apikey_value = emby_apikey.value
        
        # Fetch watch history
        watch_history = EmbyService.get_watch_history(
            emby_host_value,
            emby_apikey_value,
            days=days,
            limit=limit
        )
        
        if not watch_history:
            logger.info("No watch history found on Emby")
            return (0, 0)
            
        # Process watch history
        new_records = 0
        updated_records = 0
        
        for item in watch_history:
            # Extract item data
            item_id = item.get("Id", "")
            if not item_id:
                continue
                
            # Determine content type
            content_type = "movie"
            if item.get("Type") == "Episode":
                content_type = "episode"
            
            # Extract play timestamp and progress
            played_at = None
            if "DatePlayed" in item:
                played_at = datetime.fromisoformat(item["DatePlayed"].replace("Z", "+00:00"))
            
            # Convert ticks to seconds and calculate progress
            play_progress = 100.0  # Default to fully watched
            duration = 0
            
            if "RunTimeTicks" in item and item["RunTimeTicks"] > 0:
                # Convert ticks to seconds (1 tick = 100 nanoseconds)
                duration = int(item["RunTimeTicks"] / 10000000)
                
                if "PlaybackPositionTicks" in item and item["PlaybackPositionTicks"] > 0:
                    position_seconds = int(item["PlaybackPositionTicks"] / 10000000)
                    play_progress = min(100.0, (position_seconds / duration) * 100)
            
            # Extract metadata
            title = item.get("Name", "")
            original_title = item.get("OriginalTitle", "")
            year = item.get("ProductionYear")
            overview = item.get("Overview", "")
            genres = ", ".join(item.get("Genres", [])) if "Genres" in item else ""
            runtime = int(duration / 60) if duration > 0 else None  # Convert to minutes
            
            # TV series specific fields
            series_name = None
            season_number = -1
            episode_number = -1
            
            if content_type == "episode":
                series_name = item.get("SeriesName", "")
                if "ParentIndexNumber" in item:
                    season_number = item["ParentIndexNumber"]
                if "IndexNumber" in item:
                    episode_number = item["IndexNumber"]
            
            # Extract external IDs
            provider_ids = item.get("ProviderIds", {})
            imdb_id = provider_ids.get("Imdb", "")
            tmdb_id = provider_ids.get("Tmdb", "")
            tvdb_id = provider_ids.get("Tvdb", "")
            
            # Get play count
            play_count = item.get("PlayCount", 1)
            
            # 查找或创建MediaItem
            media_item = None
            
            # 按外部ID查找
            if imdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.imdb_id == imdb_id).first()
            if not media_item and tmdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.tmdb_id == tmdb_id).first()
            if not media_item and tvdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.tvdb_id == tvdb_id).first()
                
            # 如果没找到，按标题和年份查找
            if not media_item:
                query = session.query(MediaItem).filter(MediaItem.title == title)
                if year:
                    query = query.filter(MediaItem.year == year)
                media_item = query.first()
            
            # 如果是剧集，先查找或创建剧集
            series_item = None
            if content_type == "episode" and series_name:
                # 查找剧集
                series_query = session.query(MediaItem).filter(
                    MediaItem.media_type == "show",
                    MediaItem.title == series_name
                )
                series_item = series_query.first()
                
                # 如果没找到，创建新的剧集
                if not series_item:
                    series_item = MediaItem(
                        media_type="show",
                        title=series_name,
                        year=year
                    )
                    session.add(series_item)
                    session.flush()  # 获取ID
            
            # 如果仍然没找到，创建新的MediaItem
            if not media_item:
                media_item = MediaItem(
                    media_type=content_type,
                    title=title,
                    original_title=original_title,
                    year=year,
                    imdb_id=imdb_id,
                    tmdb_id=tmdb_id,
                    tvdb_id=tvdb_id
                )
                
                # 如果是剧集，设置剧集信息
                if content_type == "episode" and series_item:
                    media_item.series_id = series_item.id
                    media_item.season_number = season_number
                    media_item.episode_number = episode_number
                
                session.add(media_item)
                session.flush()  # 获取ID
            
            # 检查是否已存在观看记录
            existing_record = session.query(WatchHistory).filter(
                WatchHistory.source == "emby",
                WatchHistory.external_id == item_id).first()
            
            # 创建或更新观看记录
            if existing_record:
                # 更新关联的MediaItem
                existing_record.media_item_id = media_item.id
                
                # 只有在新日期更晚时才更新played_at
                if played_at and (not existing_record.played_at or played_at > existing_record.played_at):
                    existing_record.played_at = played_at
                
                existing_record.play_count = play_count
                existing_record.play_progress = play_progress
                existing_record.duration = duration
                
                updated_records += 1
            else:
                # 创建新记录
                new_record = WatchHistory(
                    source="emby",
                    external_id=item_id,
                    media_item_id=media_item.id,
                    played_at=played_at,
                    play_count=play_count,
                    play_progress=play_progress,
                    duration=duration
                )
                session.add(new_record)
                new_records += 1
        
        return (new_records, updated_records)
        
    except Exception as e:
        logger.error(f"Error syncing from Emby: {str(e)}")
        raise


def sync_jellyfin_history(session, days=30, limit=100):
    """Syncs watch history from Jellyfin
    
    Args:
        session: Database session
        days (int): Number of days of history to fetch
        limit (int): Maximum number of items to fetch
    
    Returns:
        tuple: (new_records, updated_records)
    """
    try:
        # Get Jellyfin configuration
        jellyfin_host = session.query(SystemSetting).filter(SystemSetting.key == "jellyfin_host").first()
        jellyfin_apikey = session.query(SystemSetting).filter(SystemSetting.key == "jellyfin_apikey").first()
        jellyfin_userid = session.query(SystemSetting).filter(SystemSetting.key == "jellyfin_userid").first()
        
        if not jellyfin_host or not jellyfin_apikey:
            logger.info("Jellyfin host or API key not configured")
            return (0, 0)
            
        # Extract the actual values
        jellyfin_host_value = jellyfin_host.value
        jellyfin_apikey_value = jellyfin_apikey.value
        jellyfin_userid_value = jellyfin_userid.value if jellyfin_userid else None
        
        # Fetch watch history
        watch_history = JellyfinService.get_watch_history(
            jellyfin_host_value,
            jellyfin_apikey_value,
            jellyfin_userid_value,
            days=days,
            limit=limit
        )
        
        if not watch_history:
            logger.info("No watch history found on Jellyfin")
            return (0, 0)
            
        # Process watch history
        new_records = 0
        updated_records = 0
        
        for item in watch_history:
            # Extract item data
            item_id = item.get("Id", "")
            if not item_id:
                continue
                
            # Determine content type
            content_type = "movie"
            if item.get("Type") == "Episode":
                content_type = "episode"
            
            # Extract play timestamp and progress
            played_at = None
            if "DateLastPlayed" in item:
                played_at = datetime.fromisoformat(item["DateLastPlayed"].replace("Z", "+00:00"))
            
            # Calculate progress
            play_progress = 100.0  # Default to fully watched
            duration = 0
            
            if "RunTimeTicks" in item and item["RunTimeTicks"] > 0:
                # Convert ticks to seconds (1 tick = 100 nanoseconds)
                duration = int(item["RunTimeTicks"] / 10000000)
                
                if "PlaybackPositionTicks" in item and item["PlaybackPositionTicks"] > 0:
                    position_seconds = int(item["PlaybackPositionTicks"] / 10000000)
                    play_progress = min(100.0, (position_seconds / duration) * 100)
            
            # Extract metadata
            title = item.get("Name", "")
            original_title = item.get("OriginalTitle", "")
            year = item.get("ProductionYear")
            overview = item.get("Overview", "")
            genres = ", ".join(item.get("Genres", [])) if "Genres" in item else ""
            runtime = int(duration / 60) if duration > 0 else None  # Convert to minutes
            
            # TV series specific fields
            series_name = None
            season_number = -1
            episode_number = -1
            
            if content_type == "episode":
                series_name = item.get("SeriesName", "")
                if "ParentIndexNumber" in item:
                    season_number = item["ParentIndexNumber"]
                if "IndexNumber" in item:
                    episode_number = item["IndexNumber"]
            
            # Extract external IDs
            provider_ids = item.get("ProviderIds", {})
            imdb_id = provider_ids.get("Imdb", "")
            tmdb_id = provider_ids.get("Tmdb", "")
            tvdb_id = provider_ids.get("Tvdb", "")
            
            # Get play count
            play_count = item.get("PlayCount", 1)
            
            # 查找或创建MediaItem
            media_item = None
            
            # 按外部ID查找
            if imdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.imdb_id == imdb_id).first()
            if not media_item and tmdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.tmdb_id == tmdb_id).first()
            if not media_item and tvdb_id:
                media_item = session.query(MediaItem).filter(MediaItem.tvdb_id == tvdb_id).first()
                
            # 如果没找到，按标题和年份查找
            if not media_item:
                query = session.query(MediaItem).filter(MediaItem.title == title)
                if year:
                    query = query.filter(MediaItem.year == year)
                media_item = query.first()
            
            # 如果是剧集，先查找或创建剧集
            series_item = None
            if content_type == "episode" and series_name:
                # 查找剧集
                series_query = session.query(MediaItem).filter(
                    MediaItem.media_type == "show",
                    MediaItem.title == series_name
                )
                series_item = series_query.first()
                
                # 如果没找到，创建新的剧集
                if not series_item:
                    series_item = MediaItem(
                        media_type="show",
                        title=series_name,
                        year=year
                    )
                    session.add(series_item)
                    session.flush()  # 获取ID
            
            # 如果仍然没找到，创建新的MediaItem
            if not media_item:
                media_item = MediaItem(
                    media_type=content_type,
                    title=title,
                    original_title=original_title,
                    year=year,
                    imdb_id=imdb_id,
                    tmdb_id=tmdb_id,
                    tvdb_id=tvdb_id
                )
                
                # 如果是剧集，设置剧集信息
                if content_type == "episode" and series_item:
                    media_item.series_id = series_item.id
                    media_item.season_number = season_number
                    media_item.episode_number = episode_number
                
                session.add(media_item)
                session.flush()  # 获取ID
            
            # 检查是否已存在观看记录
            existing_record = session.query(WatchHistory).filter(
                WatchHistory.source == "jellyfin",
                WatchHistory.external_id == item_id).first()
            
            # 创建或更新观看记录
            if existing_record:
                # 更新关联的MediaItem
                existing_record.media_item_id = media_item.id
                
                # 只有在新日期更晚时才更新played_at
                if played_at and (not existing_record.played_at or played_at > existing_record.played_at):
                    existing_record.played_at = played_at
                
                existing_record.play_count = play_count
                existing_record.play_progress = play_progress
                existing_record.duration = duration
                
                updated_records += 1
            else:
                # 创建新记录
                new_record = WatchHistory(
                    source="jellyfin",
                    external_id=item_id,
                    media_item_id=media_item.id,
                    played_at=played_at,
                    play_count=play_count,
                    play_progress=play_progress,
                    duration=duration
                )
                session.add(new_record)
                new_records += 1
        
        return (new_records, updated_records)
        
    except Exception as e:
        logger.error(f"Error syncing from Jellyfin: {str(e)}")
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='watch_history:link_metadata')
def celery_link_metadata_to_watch_history(self):
    """将特殊影片的Metadata关联到WatchHistory
    
    通过标题匹配或其他方式，尝试将特殊影片的Metadata关联到WatchHistory
    """
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "linking metadata to watch history: start"})
    logger.info("[+] 开始关联特殊影片元数据到观看历史")
    
    session = SessionFactory()
    try:
        # 导入模型
        from bonita.db.models.media_item import MediaItem
        from bonita.db.models.metadata import Metadata
        
        # 获取所有有number的MediaItem
        media_items_with_number = session.query(MediaItem).filter(
            MediaItem.number != None,
            MediaItem.number != ''
        ).all()
        
        logger.info(f"[+] 找到 {len(media_items_with_number)} 个带番号的媒体项")
        
        # 获取所有Metadata
        metadata_records = session.query(Metadata).all()
        
        # 创建番号到Metadata的映射
        number_to_metadata = {}
        for metadata in metadata_records:
            if metadata.number:
                number_to_metadata[metadata.number] = metadata
        
        logger.info(f"[+] 找到 {len(number_to_metadata)} 个带番号的元数据记录")
        
        # 关联MediaItem和Metadata
        linked_count = 0
        for media_item in media_items_with_number:
            if media_item.number in number_to_metadata:
                metadata = number_to_metadata[media_item.number]
                
                # 检查是否已关联
                if metadata.media_item_id != media_item.id:
                    metadata.media_item_id = media_item.id
                    linked_count += 1
        
        # 查找没有number但可能通过标题匹配的MediaItem
        media_items_without_number = session.query(MediaItem).filter(
            (MediaItem.number == None) | (MediaItem.number == '')
        ).all()
        
        title_match_count = 0
        for media_item in media_items_without_number:
            # 查找标题匹配的Metadata
            matching_metadata = session.query(Metadata).filter(
                Metadata.title == media_item.title
            ).first()
            
            if matching_metadata and not matching_metadata.media_item_id:
                # 更新MediaItem的number
                media_item.number = matching_metadata.number
                # 关联Metadata到MediaItem
                matching_metadata.media_item_id = media_item.id
                title_match_count += 1
        
        session.commit()
        logger.info(f"[+] 成功关联 {linked_count} 个番号匹配的记录和 {title_match_count} 个标题匹配的记录")
        
        self.update_state(state="PROGRESS", meta={"progress": 100, "step": "linking metadata to watch history: complete"})
        return {"linked_by_number": linked_count, "linked_by_title": title_match_count}
        
    except Exception as e:
        logger.error(f"关联元数据时出错: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()
