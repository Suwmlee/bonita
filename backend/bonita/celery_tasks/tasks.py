import os
import logging
import re
from datetime import datetime
from celery import shared_task, group
from celery.result import allow_join_result

from multiprocessing import Semaphore

from bonita import schemas
from bonita.db import SessionFactory
from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.metadata import Metadata
from bonita.db.models.record import TransRecords
from bonita.db.models.setting import ScrapingSetting
from bonita.modules.scraping.number_parser import FileNumInfo
from bonita.modules.scraping.scraping import add_mark, process_nfo_file, process_cover, scraping
from bonita.modules.transfer.fileinfo import FileInfo
from bonita.modules.transfer.transfer import transSingleFile, transferfile, findAllVideos
from bonita.utils.downloader import get_cached_file
from bonita.utils.filehelper import video_type


# 创建信号量，最多允许 5 个任务同时执行
max_concurrent_tasks = 5
semaphore = Semaphore(max_concurrent_tasks)

logger = logging.getLogger(__name__)


def process_watcher_task(task_conf_id: int):
    """
    执行任务
    """
    logger.info(f"process watcher task: {task_conf_id}")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:all')
def celery_transfer_entry(self, task_json):
    """ 转移任务入口
    """
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "transfer task: start"})
    task_info = schemas.TransferTaskPublic(**task_json)
    logger.info(f"transfer task {task_info.id}: start")
    # 获取 source 文件夹下所有顶层文件/文件夹
    dirs = os.listdir(task_info.source_folder)

    task_group = group(celery_transfer_group.s(task_json, os.path.join(
        task_info.source_folder, single_folder)) for single_folder in dirs)

    if task_info.clean_others:
        task_group.tasks.append(celery_clean_others.s(task_json))

    result = task_group.apply_async()

    return result


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:group')
def celery_transfer_group(self, task_json, full_path):
    """ 对 group/folder 内所有关联文件进行转移
    """
    with semaphore:
        self.update_state(state="PROGRESS", meta={"progress": 0, "step": "celery_transfer_pool: start"})
        logger.info(f"transfer group start {full_path}")
        task_info = schemas.TransferTaskPublic(**task_json)
        fixseries = False
        if task_info.content_type == 2:
            fixseries = True

        if os.path.isdir(full_path):
            waiting_list = findAllVideos(full_path, task_info.source_folder, re.split("[,，]", task_info.escape_folder))
        else:
            if not os.path.splitext(full_path)[1].lower() in video_type:
                logger.debug(f"[!] Transfer failed {full_path}")
                return []
            waiting_list = []
            tf = FileInfo(full_path)
            # 最顶层是文件情况，midfolder 应为 ''
            # midfolder = tf.realfolder.replace(task_info.source_folder, '').lstrip("\\").lstrip("/")
            tf.updateMidFolder('')
            if tf.topfolder != '.':
                tf.parse()
            waiting_list.append(tf)

        logger.debug(f"[+] Transfer check {full_path}")
        # 创建一个新的数据库会话
        try:
            session = SessionFactory()

            done_list = []
            for currentfile in waiting_list:
                if not isinstance(currentfile, FileInfo):
                    continue
                record = session.query(TransRecords).filter(TransRecords.srcpath == currentfile.realpath).first()
                if not record:
                    record = TransRecords()
                    record.srcname = currentfile.name
                    record.srcpath = currentfile.realpath
                    session.add(record)
                    session.commit()
                if task_info.sc_enabled:
                    logger.debug(f"[-] need scraping")
                    scraping_conf = session.query(ScrapingSetting).filter(ScrapingSetting.id == task_info.sc_id).first()
                    if not scraping_conf:
                        logger.debug(f"[-] scraping config not found")
                        continue
                    scraping_task = celery_scrapping.apply(args=[currentfile.realpath, scraping_conf.to_dict()])
                    with allow_join_result():
                        metabase_json = scraping_task.get()
                    if not metabase_json:
                        logger.debug(f"[-] scraping failed")
                        continue
                    metamixed = schemas.MetadataMixed.model_validate(metabase_json)

                    output_folder = os.path.abspath(os.path.join(task_info.output_folder, metamixed.extra_folder))
                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)
                    # 写入NFO文件
                    process_nfo_file(output_folder, metamixed.extra_filename, metamixed.__dict__)
                    cache_cover_filepath = get_cached_file(session, metamixed.cover, metamixed.number)
                    pics = process_cover(cache_cover_filepath, output_folder, metamixed.extra_filename)
                    if scraping_conf.watermark_enabled:
                        add_mark(pics, metamixed.tag, scraping_conf.watermark_location, scraping_conf.watermark_size)
                    # 移动
                    destpath = transSingleFile(currentfile, output_folder, metamixed.extra_filename, task_info.operation)
                    done_list.append(destpath)
                    # 更新
                    record.destpath = destpath
                    record.updatetime = datetime.now()
                    logger.debug(f"[-] scraping transfer end")
                else:
                    logger.debug(f"[-] start transfer")
                    # 开始转移
                    destpath = transferfile(currentfile, task_info.source_folder, simplify_tag=task_info.optimize_name,
                                            fixseries_tag=fixseries, dest_folder=task_info.output_folder,
                                            movie_list=waiting_list, linktype=task_info.operation)
                    done_list.append(destpath)
                    # 更新
                    record.destpath = destpath
                    record.updatetime = datetime.now()
                    logger.debug(f"[-] transfer end")
        except Exception as e:
            logger.error(e)
        finally:
            session.commit()
            session.close()

        logger.info(f"transfer group end {full_path}")
        return done_list


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='scraping:single')
def celery_scrapping(self, file_path, scraping_dict):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "scraping task: start"})
    logger.debug(f"[+] scraping task: start")
    try:
        session = SessionFactory()
        scraping_conf = schemas.ScrapingSettingPublic(**scraping_dict)
        # 根据路径获取额外自定义信息
        fileNumInfo = FileNumInfo(file_path)
        extrainfo = session.query(ExtraInfo).filter(ExtraInfo.filepath == file_path).first()
        if not extrainfo:
            extrainfo = ExtraInfo(filepath=file_path)
            extrainfo.number = fileNumInfo.num
            extrainfo.partNumber = int(fileNumInfo.part.replace("-CD", "")) if fileNumInfo.part else 0
            extrainfo.tag = ', '.join(map(str, fileNumInfo.tags()))
            session.add(extrainfo)
        # TODO 处理指定源/强制从网站更新
        metadata_record = session.query(Metadata).filter(Metadata.number == extrainfo.number).first()
        if metadata_record:
            metadata_mixed = schemas.MetadataMixed(**metadata_record.to_dict())
        else:
            # scraping
            metadata_base = scraping(extrainfo.number,
                                     scraping_conf.scraping_sites,
                                     extrainfo.specifiedsource,
                                     extrainfo.specifiedurl)
            # 保存 metadata 到数据库
            filter_dict = Metadata.filter_dict(Metadata, metadata_base.__dict__)
            metadata_record = Metadata(**filter_dict)
            if scraping_conf.save_metadata:
                session.add(metadata_record)
            metadata_mixed = schemas.MetadataMixed(**metadata_record.to_dict())

        # 根据规则生成文件夹和文件名
        maxlen = scraping_conf.max_title_len
        extra_folder = eval(scraping_conf.location_rule, metadata_mixed.__dict__)
        if 'actor' in scraping_conf.location_rule and len(metadata_mixed.actor) > 100:
            extra_folder = eval(scraping_conf.location_rule.replace("actor", "'多人作品'"), metadata_mixed.__dict__)
        if 'title' in scraping_conf.location_rule and len(metadata_mixed.title) > maxlen:
            shorttitle = metadata_mixed.title[0:maxlen]
            extra_folder = extra_folder.replace(metadata_mixed.title, shorttitle)
        metadata_mixed.extra_folder = extra_folder
        metadata_mixed.extra_filename = eval(scraping_conf.naming_rule, metadata_mixed.__dict__)

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
def celery_clean_others(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "clean others: start"})
    logger.debug(f"[+] clean others: start")

    # if task_info.clean_others:
    #     for donefile in done_list:
    #         if donefile in old_list:
    #             old_list.remove(donefile)
    #         else:
    #             os.remove(donefile)
    #     if os.path.isdir(full_path):
    #         cleanExtraMedia(full_path)
    #         cleanFolderWithoutSuffix(full_path, video_type)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='emby:scan')
def celery_emby_scan(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "emby scan: start"})
    logger.debug(f"[+] emby scan: start")
