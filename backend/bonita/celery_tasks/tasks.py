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
from bonita.modules.scraping.number_parser import FileNumInfo
from bonita.modules.scraping.scraping import add_mark, process_nfo_file, process_cover, scraping, load_all_NFO_from_folder
from bonita.utils.fileinfo import BasicFileInfo, TargetFileInfo
from bonita.modules.transfer.transfer import transSingleFile, transferfile
from bonita.utils.downloader import process_cached_file, update_cache_from_local
from bonita.utils.filehelper import cleanFolderWithoutSuffix, findAllFilesWithSuffix, video_type
from bonita.utils.http import get_active_proxy
from bonita.modules.media_service.emby import EmbyService


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
    dirs = os.scandir(task_info.source_folder)

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

        waiting_list = []
        if os.path.isdir(full_path):
            escape_folders = [fo.strip() for fo in task_info.escape_folder.split(',')]
            allvideo_list = findAllFilesWithSuffix(full_path, video_type, escape_folders)
            for video in allvideo_list:
                tf = BasicFileInfo(video)
                tf.set_root_folder(task_info.source_folder)
                waiting_list.append(tf)
        else:
            if not os.path.splitext(full_path)[1].lower() in video_type:
                logger.info(f"[!] Transfer failed {full_path}")
                return []
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
                record.success = None
                if task_info.sc_enabled:
                    logger.info(f"[-] need scraping")
                    scraping_conf = session.query(ScrapingConfig).filter(ScrapingConfig.id == task_info.sc_id).first()
                    if not scraping_conf:
                        logger.info(f"[-] scraping config not found")
                        record.success = False
                        continue
                    scraping_task = celery_scrapping.apply(args=[original_file.full_path, scraping_conf.to_dict()])
                    with allow_join_result():
                        metabase_json = scraping_task.get()
                    if not metabase_json:
                        logger.error(f"[-] scraping failed {original_file.full_path}")
                        record.success = False
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
                    logger.info(f"[-] transfer end")
                # 更新 record 状态
                record.deleted = False
                record.success = True
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
            metadata_base.number = metadata_base.number.upper()
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
def celery_clean_others(self, root_path, done_list):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "clean others: start"})
    logger.info(f"[+] clean others task for {root_path}: start")

    cleaned_files = []
    dest_list = findAllFilesWithSuffix(root_path, video_type)
    for dest in dest_list:
        if dest not in done_list:
            cleaned_files.append(dest)
    for torm in cleaned_files:
        logger.info(f"[!] remove other file: [{torm}]")
        os.remove(torm)
    cleanFolderWithoutSuffix(root_path, video_type)

    logger.info(f"Clean others completed. Removed {len(cleaned_files)} files")
    return cleaned_files


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='emby:scan')
def celery_emby_scan(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "emby scan: start"})
    logger.info(f"[+] emby scan: start")
    try:
        emby_service = EmbyService()
        if not emby_service.is_initialized:
            from bonita.core.service import init_emby
            init_emby()
        emby_service.trigger_library_scan()
    except Exception as e:
        logger.error(f"Error during Emby library scan: {str(e)}")


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
