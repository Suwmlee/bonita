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
from bonita.modules.scraping.scraping import add_mark, need_crop, process_nfo_file, process_cover, scraping, load_all_NFO_from_folder
from bonita.utils.fileinfo import BasicFileInfo, TargetFileInfo
from bonita.modules.transfer.transfer import transSingleFile, transferfile
from bonita.utils.downloader import process_cached_file, update_cache_from_local
from bonita.utils.filehelper import cleanFolderWithoutSuffix, findAllFilesWithSuffix, video_type
from bonita.utils.http import get_active_proxy
from bonita.modules.media_service.emby import EmbyService
from bonita.modules.media_service.sync import sync_emby_history
from bonita.celery_tasks.decorators import manage_celery_task
from bonita.services.celery_service import TaskProgressTracker
from bonita.services.setting_service import SettingService


# 创建信号量，最多允许X任务同时执行
max_concurrent_tasks = settings.MAX_CONCURRENT_TASKS
semaphore = Semaphore(max_concurrent_tasks)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:all')
@manage_celery_task("TransferAll")
def celery_transfer_entry(self, task_json):
    """ 转移任务入口
    """
    task_id = self.request.id
    progress_tracker = TaskProgressTracker(task_id, 100)
    progress_tracker.set_progress(5, "初始化转移任务")
    task_info = schemas.TransferConfigPublic(**task_json)
    progress_tracker.update_detail(task_info.id)

    logger.info(f"## [转移任务] START - ID:{task_info.id} | 源:{task_info.source_folder} → 目标:{task_info.output_folder}")
    
    # 获取 source 文件夹下所有顶层文件/文件夹
    progress_tracker.set_progress(15, "扫描源文件夹")
    dirs = os.scandir(task_info.source_folder)

    # 创建转移任务组
    progress_tracker.set_progress(25, "创建转移任务组")
    transfer_group = group(celery_transfer_group.s(task_json, os.path.join(
        task_info.source_folder, single_folder)) for single_folder in dirs)

    # 先执行所有转移任务
    progress_tracker.set_progress(35, "执行转移任务")
    transfer_result = transfer_group.apply_async()

    # 使用 allow_join_result 上下文管理器等待转移任务完成
    progress_tracker.set_progress(50, "等待转移任务完成")
    with allow_join_result():
        done_list = transfer_result.get()
        progress_tracker.set_progress(70, "处理转移结果")
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
        logger.info(f"  ✓ 转移完成 - 共处理 {len(done_list)} 个文件")

        # 转移完成后，判断是否执行清理任务或扫描任务
        progress_tracker.set_progress(85, "执行后续任务")
        if task_info.clean_others:
            logger.info(f"  → 触发清理任务")
            celery_clean_others.apply_async(args=[task_info.output_folder, done_list])
        if task_info.auto_watch:
            logger.info(f"  → 触发媒体库扫描")
            celery_emby_scan.apply_async(args=[task_json])

    progress_tracker.complete("转移任务完成")
    logger.info(f"## [转移任务] END - ID:{task_info.id}")

    return True


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:group')
@manage_celery_task("TransferGroup")
def celery_transfer_group(self, task_json, full_path, isEntry=False):
    """ 对 group/folder 内所有关联文件进行转移
    """
    with semaphore:
        task_id = self.request.id
        progress_tracker = TaskProgressTracker(task_id, 100)
        progress_tracker.set_progress(5, "开始处理文件组")
        progress_tracker.update_detail(full_path)

        logger.info(f"  ▸ [文件组] {full_path}")
        if not os.path.exists(full_path):
            logger.warning(f"    ✗ 路径不存在")
            return []

        progress_tracker.set_progress(15, "解析任务配置")
        task_info = schemas.TransferConfigPublic(**task_json)
        is_series = False
        if task_info.content_type == 2:
            is_series = True

        progress_tracker.set_progress(25, "扫描待处理文件")
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
                logger.warning(f"    ✗ 非视频文件，跳过")
                return []
            tf = BasicFileInfo(full_path)
            tf.set_root_folder(task_info.source_folder)
            waiting_list.append(tf)

        logger.info(f"    找到 {len(waiting_list)} 个文件")
        progress_tracker.set_progress(40, f"开始处理 {len(waiting_list)} 个文件")
        try:
            session = SessionFactory()
            done_list = []
            total_files = len(waiting_list)
            for idx, original_file in enumerate(waiting_list):
                # 更新当前文件处理进度
                if total_files > 0:
                    file_progress = 40 + (50 * idx // total_files)
                    progress_tracker.set_progress(
                        file_progress, f"处理文件 {idx+1}/{total_files}: {original_file.filename if hasattr(original_file, 'filename') else 'unknown'}")
                if not isinstance(original_file, BasicFileInfo):
                    continue
                
                logger.info(f"    [{idx+1}/{total_files}] {original_file.filename}")
                
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
                    logger.info(f"      ⊘ 已忽略")
                    continue
                record.task_id = task_info.id
                record.success = None
                if task_info.sc_enabled:
                    logger.info(f"      → 刮削模式")
                    scraping_conf = session.query(ScrapingConfig).filter(ScrapingConfig.id == task_info.sc_id).first()
                    if not scraping_conf:
                        logger.error(f"      ✗ 刮削配置未找到")
                        record.success = False
                        continue
                    scraping_task = celery_scrapping.apply(args=[original_file.full_path, scraping_conf.to_dict()])
                    with allow_join_result():
                        metabase_json = scraping_task.get()
                    if not metabase_json:
                        logger.error(f"      ✗ 刮削失败")
                        record.success = False
                        continue
                    metamixed = schemas.MetadataMixed.model_validate(metabase_json)

                    # 验证结果路径在 output_folder 下，例如：extra_folder 不能"/"开头导致join失败
                    output_folder = os.path.abspath(os.path.join(task_info.output_folder, metamixed.extra_folder))
                    base_output = os.path.abspath(task_info.output_folder)
                    if not output_folder.startswith(base_output):
                        logger.error(f"      ✗ 安全检查失败，使用基础目录")
                        output_folder = base_output
                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)
                    # 更新NFO文件/cover
                    process_nfo_file(output_folder, metamixed.extra_filename, metamixed.__dict__)
                    cache_cover_filepath = process_cached_file(session, metamixed.cover, metamixed.number)
                    pics = process_cover(cache_cover_filepath, output_folder, metamixed.extra_filename, crop=metamixed.extra_crop)
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
                    logger.info(f"      ✓ 刮削转移完成")
                else:
                    logger.info(f"      → 直接转移")
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
                    logger.info(f"      ✓ 直接转移完成")
                # 更新 record 状态
                record.deleted = False
                record.success = True
        except Exception as e:
            logger.error(e)
        finally:
            session.commit()
            session.close()

        progress_tracker.set_progress(95, "处理后续任务")
        if isEntry and task_info.auto_watch:
            try:
                celery_emby_scan.apply(args=[task_json])
            except Exception as e:
                logger.error(f"    ✗ Emby 扫描失败: {e}")

        progress_tracker.complete(f"文件组转移完成，处理了 {len(done_list)} 个文件")
        logger.info(f"  ▸ [文件组] 完成 - {len(done_list)} 个文件")
        return done_list


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='scraping:single')
def celery_scrapping(self, file_path, scraping_dict):
    logger.info(f"    ▸ [刮削] {os.path.basename(file_path)}")
    try:
        session = SessionFactory()
        scraping_conf = schemas.ScrapingConfigPublic(**scraping_dict)
        # 根据路径获取额外自定义信息
        fileNumInfo = FileNumInfo(file_path)
        extrainfo = session.query(ExtraInfo).filter(ExtraInfo.filepath == file_path).first()
        if not extrainfo:
            extrainfo = ExtraInfo(filepath=file_path)
            extrainfo.number = fileNumInfo.num
            if not need_crop(extrainfo.number):
                extrainfo.crop = False
            extrainfo.partNumber = int(fileNumInfo.part.replace("-CD", "")) if fileNumInfo.part else 0
            extrainfo.tag = ', '.join(map(str, fileNumInfo.tags()))
            extrainfo.create(session)
        else:
            if extrainfo.crop is None:
                if need_crop(extrainfo.number):
                    extrainfo.crop = True
                else:
                    extrainfo.crop = False
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
            logger.info(f"      ✓ 使用缓存: {metadata_record.number}")
            metadata_mixed = schemas.MetadataMixed(**metadata_record.to_dict())
        else:
            # 如果没有找到任何记录，则从网络抓取
            logger.info(f"      → 网络抓取: {extrainfo.number}")
            proxy = get_active_proxy(session)
            json_data = scraping(extrainfo.number,
                                 scraping_conf.scraping_sites,
                                 extrainfo.specifiedsource,
                                 extrainfo.specifiedurl,
                                 proxy
                                 )
            # Return if blank dict returned (data not found)
            if not json_data:
                logger.error(f"      ✗ 抓取失败")
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

        # 清理和验证生成的路径
        # 移除路径中的非法字符
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in illegal_chars:
            extra_folder = extra_folder.replace(char, '_')
            extra_name = extra_name.replace(char, '_')
        # 确保路径不为空且不是绝对路径
        extra_folder = extra_folder.strip()
        if not extra_folder or extra_folder.startswith('/') or extra_folder.startswith('\\'):
            extra_folder = metadata_mixed.actor if metadata_mixed.actor else '未分类'
        # 移除路径开头的斜杠和点
        extra_folder = extra_folder.lstrip('/\\.')
        # 替换路径遍历字符
        extra_folder = extra_folder.replace('..', '_')

        metadata_mixed.extra_folder = extra_folder
        metadata_mixed.extra_filename = extra_name
        metadata_mixed.extra_crop = extrainfo.crop

        # 将 extrainfo.tag 中的标签添加到 metadata_base.tag 中，过滤重复的标签
        existing_tags = set(metadata_mixed.tag.split(", ")) if metadata_mixed.tag else set()
        new_tags = set(extrainfo.tag.split(", ")) if extrainfo.tag else set()
        combined_tags = existing_tags.union(new_tags)
        # 过滤掉空字符串
        combined_tags = {tag for tag in combined_tags if tag.strip()}
        metadata_mixed.tag = ", ".join(combined_tags) if combined_tags else ''
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
    logger.info(f"## [清理任务] START - {root_path}")

    cleaned_files = []
    dest_list = findAllFilesWithSuffix(root_path, video_type)
    for dest in dest_list:
        if dest not in done_list:
            cleaned_files.append(dest)
    for torm in cleaned_files:
        logger.info(f"  ✗ 删除: {os.path.basename(torm)}")
        os.remove(torm)
    cleanFolderWithoutSuffix(root_path, video_type)

    logger.info(f"## [清理任务] END - 删除 {len(cleaned_files)} 个文件")
    return cleaned_files


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='emby:scan')
def celery_emby_scan(self, task_json):
    logger.info(f"## [Emby扫描] START")
    try:
        emby_service = EmbyService()
        if not emby_service.is_initialized:
            from bonita.core.service import init_emby
            init_emby()
        emby_service.trigger_library_scan()
        logger.info(f"## [Emby扫描] END")
    except Exception as e:
        logger.error(f"## [Emby扫描] ✗ 失败: {str(e)}")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='import:nfo')
def celery_import_nfo(self, folder_path, option):
    logger.info(f"## [NFO导入] START - {folder_path}")
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
        logger.info(f"  找到 {len(filtered_metadata_list)} 个有效 NFO 文件")
        for nfo_dict in metadata_list:
            nfo_data = nfo_dict['nfo']
            cover_path = nfo_dict['cover_path']

            # 确保 actor 字段不为空
            if not nfo_data.get('actor') or nfo_data.get('actor', '').strip() == '':
                nfo_data['actor'] = '佚名'

            try:
                metadata_base = schemas.MetadataBase(**nfo_data)
                # 如果 title 中包含 number，则删除 number
                if metadata_base.number in metadata_base.title:
                    metadata_base.title = metadata_base.title.replace(metadata_base.number, '').strip(' -')
            except Exception as e:
                logger.error(f"  ✗ NFO转换失败: {str(e)}")
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
                logger.error(f"  ✗ 导入失败 {os.path.basename(nfo_dict['nfo_path'])}: {str(e)}")
                continue
            finally:
                session.close()
        logger.info(f"## [NFO导入] END")
    except Exception as e:
        logger.error(f"## [NFO导入] ✗ 失败: {str(e)}")
    return True


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='watch_history:sync')
def celery_sync_watch_history(self, sources=None, days=30, limit=100):
    """
    同步观看历史的Celery任务

    Args:
        sources: 需要同步的媒体来源列表，None表示全部启用来源
        days: 历史同步天数，预留参数
        limit: 单次同步的数据量限制，预留参数
    """
    logger.info(f"## [观看历史同步] START - 来源:{sources}")
    session = SessionFactory()
    requested_sources = sources
    if not requested_sources:
        requested_sources = ["emby"]
    elif isinstance(requested_sources, str):
        requested_sources = [requested_sources]
    else:
        requested_sources = list(requested_sources)

    synced_sources = []

    try:
        setting_service = SettingService(session)

        if "emby" in requested_sources:
            emby_settings = setting_service.get_emby_settings()
            if emby_settings.get("enabled"):
                emby_service = EmbyService()
                if not emby_service.is_initialized:
                    try:
                        from bonita.core.service import init_emby
                        init_emby()
                    except Exception as init_error:
                        logger.error(f"  ✗ Emby 初始化失败: {init_error}")
                if emby_service.is_initialized:
                    sync_emby_history(session)
                    synced_sources.append("emby")
                    logger.info(f"  ✓ Emby 同步完成")
                else:
                    logger.warning(f"  ⊘ Emby 服务未初始化")
            else:
                logger.info(f"  ⊘ Emby 同步已禁用")

        unsupported_sources = set(requested_sources) - {"emby"}
        for source in unsupported_sources:
            logger.info(f"  ⊘ {source} 暂未支持")

        logger.info(f"## [观看历史同步] END - 已同步:{synced_sources}")
        return {
            "requested_sources": requested_sources,
            "synced_sources": synced_sources,
            "days": days,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"## [观看历史同步] ✗ 失败: {str(e)}")
        raise
    finally:
        session.close()
