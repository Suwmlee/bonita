import logging
import os
from multiprocessing import Semaphore

from celery import group, shared_task
from celery.result import allow_join_result

from bonita import schemas
from bonita.core.config import settings
from bonita.db import SessionFactory
from bonita.db.models.metadata import Metadata
from bonita.db.models.record import TransRecords
from bonita.db.models.scraping import ScrapingConfig
from bonita.modules.scraping.scraping import add_mark, process_cover, process_nfo_file, scraping
from bonita.modules.transfer.transfer import transSingleFile, transferfile
from bonita.services.celery_service import TaskProgressTracker
from bonita.tasks.decorators import manage_celery_task
from bonita.tasks.media import celery_emby_scan
from bonita.tasks.scraping import celery_scrapping
from bonita.utils.downloader import download_file, process_cached_file
from bonita.utils.filehelper import cleanFolderWithoutSuffix, findAllFilesWithSuffix, video_type
from bonita.utils.fileinfo import BasicFileInfo, TargetFileInfo
from bonita.utils.http import get_active_proxy

logger = logging.getLogger(__name__)
max_concurrent_tasks = settings.MAX_CONCURRENT_TASKS
semaphore = Semaphore(max_concurrent_tasks)


def _safe_filesize(path):
    """读取文件大小；源文件缺失时返回 -1，避免扫描阶段中断整个文件组"""
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


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
    escape_folders = set([fo.strip() for fo in task_info.escape_folder.split(',')] if task_info.escape_folder else [])
    dirs = [entry for entry in os.scandir(task_info.source_folder) if entry.name not in escape_folders]
    logger.info(f"  扫描到 {len(dirs)} 个顶层条目（已排除文件夹: {escape_folders}）")

    # 创建转移任务组
    progress_tracker.set_progress(25, "创建转移任务组")
    transfer_group = group(celery_transfer_group.s(task_json, entry.path) for entry in dirs)

    # 先执行所有转移任务
    progress_tracker.set_progress(35, "执行转移任务")
    if os.environ.get("MAX_CONCURRENCY") == "1":
        transfer_result = transfer_group.apply()
    else:
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
            logger.info("  → 触发清理任务")
            if os.environ.get("MAX_CONCURRENCY") == "1":
                celery_clean_others.apply(args=[task_info.output_folder, done_list])
            else:
                celery_clean_others.apply_async(args=[task_info.output_folder, done_list])
        if task_info.auto_watch:
            logger.info("  → 触发媒体库扫描")
            if os.environ.get("MAX_CONCURRENCY") == "1":
                celery_emby_scan.apply(args=[task_json])
            else:
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
            logger.warning("    ✗ 路径不存在")
            return []

        progress_tracker.set_progress(15, "解析任务配置")
        task_info = schemas.TransferConfigPublic(**task_json)
        is_series = False
        if task_info.content_type == 2:
            is_series = True

        progress_tracker.set_progress(25, "扫描待处理文件")
        waiting_list = []
        if os.path.isdir(full_path):
            escape_folders = [fo.strip() for fo in task_info.escape_folder.split(',')] if task_info.escape_folder else []
            allvideo_list = findAllFilesWithSuffix(full_path, video_type, escape_folders)
            for video in allvideo_list:
                tf = BasicFileInfo(video)
                tf.set_root_folder(task_info.source_folder)
                waiting_list.append(tf)
        else:
            if os.path.splitext(full_path)[1].lower() not in video_type:
                logger.warning(f"    ✗ 非视频文件，跳过: {full_path}")
                return []
            tf = BasicFileInfo(full_path)
            tf.set_root_folder(task_info.source_folder)
            waiting_list.append(tf)

        # 排除文件名包含指定文字的文件
        if task_info.escape_literals:
            escape_lits = [lit.strip() for lit in task_info.escape_literals.split(',') if lit.strip()]
            if escape_lits:
                before_count = len(waiting_list)
                waiting_list = [tf for tf in waiting_list if not any(lit in tf.filename for lit in escape_lits)]
                logger.info(f"    排除含指定文字的文件: {before_count - len(waiting_list)} 个 (规则: {escape_lits})")

        # 排除小于指定大小的文件（单位MB，0表示不排除）
        if task_info.escape_size and task_info.escape_size > 0:
            min_size_bytes = task_info.escape_size * 1024 * 1024
            before_count = len(waiting_list)
            waiting_list = [tf for tf in waiting_list if _safe_filesize(tf.full_path) >= min_size_bytes]
            logger.info(f"    排除小于 {task_info.escape_size}MB 的文件: {before_count - len(waiting_list)} 个")

        logger.info(f"    找到 {len(waiting_list)} 个文件")
        progress_tracker.set_progress(40, f"开始处理 {len(waiting_list)} 个文件")
        done_list = []
        failed_count = 0
        session = None
        try:
            session = SessionFactory()
            total_files = len(waiting_list)
            for idx, original_file in enumerate(waiting_list):
                record = None
                # 更新当前文件处理进度
                if total_files > 0:
                    file_progress = 40 + (50 * idx // total_files)
                    progress_tracker.set_progress(
                        file_progress, f"处理文件 {idx+1}/{total_files}: {original_file.filename if hasattr(original_file, 'filename') else 'unknown'}")
                if not isinstance(original_file, BasicFileInfo):
                    continue

                logger.info(f"    [{idx+1}/{total_files}] {original_file.filename}")

                try:
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
                        logger.info("      ⊘ 已忽略")
                        continue
                    if not os.path.exists(original_file.full_path):
                        logger.warning(f"      ⊘ 源文件不存在，跳过: {original_file.full_path}")
                        record.success = False
                        failed_count += 1
                        continue
                    record.task_id = task_info.id
                    record.success = None
                    if task_info.sc_enabled:
                        logger.info("      → 刮削模式")
                        scraping_conf = session.query(ScrapingConfig).filter(ScrapingConfig.id == task_info.sc_id).first()
                        if not scraping_conf:
                            logger.error("      ✗ 刮削配置未找到")
                            record.success = False
                            continue
                        scraping_task = celery_scrapping.apply(args=[original_file.full_path, scraping_conf.to_dict()])
                        with allow_join_result():
                            metabase_json = scraping_task.get()
                        if not metabase_json:
                            logger.error("      ✗ 刮削失败")
                            record.success = False
                            continue
                        metamixed = schemas.MetadataMixed.model_validate(metabase_json)

                        # 验证结果路径在 output_folder 下，例如：extra_folder 不能"/"开头导致join失败
                        output_folder = os.path.abspath(os.path.join(task_info.output_folder, metamixed.extra_folder))
                        base_output = os.path.abspath(task_info.output_folder)
                        if not output_folder.startswith(base_output):
                            logger.error("      ✗ 安全检查失败，使用基础目录")
                            output_folder = base_output
                        if not os.path.exists(output_folder):
                            os.makedirs(output_folder)
                        # 更新NFO文件/cover
                        process_nfo_file(output_folder, metamixed.extra_filename, metamixed.__dict__)

                        # 尝试下载封面，最多重试3次
                        proxy = get_active_proxy(session)
                        cache_cover_filepath = None
                        cover_url = metamixed.cover
                        retry_count = 0
                        max_retries = 3
                        used_sources = {metamixed.site} if metamixed.site else set()
                        extrafanart_list = []

                        # 收集首次刮削拿到的 extrafanart
                        raw_ef = metamixed.extrafanart or ''
                        if raw_ef:
                            ef_items = raw_ef.split(',') if isinstance(raw_ef, str) else raw_ef
                            extrafanart_list = [u.strip() for u in ef_items if u.strip()]

                        while retry_count < max_retries:
                            try:
                                cache_cover_filepath = process_cached_file(session, metamixed.cover, metamixed.number)
                                break
                            except Exception as e:
                                retry_count += 1
                                logger.warning(f"      ✗ 封面下载失败 (尝试 {retry_count}/{max_retries}): {cover_url} — {e}")
                                if retry_count >= max_retries:
                                    break
                                # 用其他源重新刮削获取封面 URL
                                all_sources = scraping_conf.scraping_sites.split(',') if scraping_conf.scraping_sites else []
                                remaining_sources = [s.strip() for s in all_sources if s.strip() and s.strip() not in used_sources]
                                if not remaining_sources:
                                    logger.warning("      ⊘ 没有可用源可继续尝试")
                                    break
                                # 指定第一个未用过的源重新刮削
                                fallback_json = scraping(
                                    metamixed.number,
                                    sources=','.join(remaining_sources[:1]),
                                    specifiedsource="",
                                    specifiedurl="",
                                    proxy=proxy
                                )
                                if fallback_json and fallback_json.get('cover'):
                                    new_site = fallback_json.get('site', '')
                                    if new_site:
                                        used_sources.add(new_site)
                                    # 收集 extrafanart
                                    ef_raw = fallback_json.get('extrafanart')
                                    if ef_raw:
                                        ef_items = ef_raw.split(',') if isinstance(ef_raw, str) else ef_raw
                                        for u in ef_items:
                                            u = u.strip()
                                            if u and u not in extrafanart_list:
                                                extrafanart_list.append(u)
                                    new_cover = fallback_json.get('cover')
                                    if new_cover and new_cover != cover_url:
                                        cover_url = new_cover
                                        continue
                                break

                        # 全部重试失败，降级到 extrafanart
                        if cache_cover_filepath is None and extrafanart_list:
                            ef_url = extrafanart_list[0]
                            logger.info(f"      → 使用 extrafanart 作为封面: {ef_url}")
                            try:
                                cache_cover_filepath = download_file(ef_url, metamixed.number, proxy)
                                cover_url = ef_url
                            except Exception as e:
                                logger.warning(f"      ⊘ extrafanart 下载失败: {e}")

                        # 更新 metadata_mixed 中的 cover 为实际使用的 URL，同时回写数据库
                        if cover_url:
                            metamixed.cover = cover_url
                            metadata_record = session.query(Metadata).filter(
                                Metadata.number == metamixed.number
                            ).order_by(Metadata.id.desc()).first()
                            if metadata_record:
                                metadata_record.cover = cover_url
                                session.commit()

                        # 有封面则处理封面图片，否则跳过
                        pics = []
                        if cache_cover_filepath:
                            pics = process_cover(cache_cover_filepath, output_folder, metamixed.extra_filename, crop=metamixed.extra_crop)
                            if scraping_conf.watermark_enabled:
                                add_mark(pics, metamixed.tag, scraping_conf.watermark_location, scraping_conf.watermark_size)
                        else:
                            logger.warning("      ⊘ 封面获取失败，跳过封面图片处理")
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
                        logger.info("      ✓ 刮削转移完成")
                    else:
                        logger.info("      → 直接转移")
                        target_file = TargetFileInfo(task_info.output_folder)
                        if record.top_folder:
                            target_file.force_update_top_folder(record.top_folder)
                        # 如果 record 中定义了剧集信息，则使用 record 中的信息
                        if record.isepisode:
                            target_file.force_update_episode(record.isepisode, record.season, record.episode)
                        # 开始转移
                        target_file = transferfile(original_file, target_file,
                                                   optimize_name_tag=task_info.optimize_name, series_tag=is_series,
                                                   file_list=waiting_list, linktype=task_info.operation,
                                                   part_number=record.part_number or 0)
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
                        logger.info("      ✓ 直接转移完成")
                    # 更新 record 状态
                    record.deleted = False
                    record.success = True
                except Exception as e:
                    failed_count += 1
                    logger.error(f"      ✗ 转移失败: {original_file.filename} — {e}")
                    if record is not None:
                        record.success = False
                    continue
        except Exception as e:
            logger.error(e)
        finally:
            if session:
                session.commit()
                session.close()

        progress_tracker.set_progress(95, "处理后续任务")
        if isEntry and task_info.auto_watch:
            try:
                celery_emby_scan.apply(args=[task_json])
            except Exception as e:
                logger.error(f"    ✗ Emby 扫描失败: {e}")

        summary = f"文件组转移完成，处理了 {len(done_list)} 个文件"
        if failed_count:
            summary += f"，失败 {failed_count} 个"
        progress_tracker.complete(summary)
        if failed_count:
            logger.warning(f"  ▸ [文件组] 完成 - {len(done_list)} 个成功, {failed_count} 个失败")
        else:
            logger.info(f"  ▸ [文件组] 完成 - {len(done_list)} 个文件")
        return done_list


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
