
import os
import datetime
import logging
import re
from celery import shared_task, group
from multiprocessing import Semaphore

from app import schemas
from app.celery_tasks.fileinfo import FileInfo
from app.db import SessionFactory
from app.db.models.record import TransRecords
from app.celery_tasks.transfer import transferfile, findAllVideos
from app.utils.filehelper import cleanExtraMedia, cleanFolderWithoutSuffix, video_type

# 创建信号量，最多允许 5 个任务同时执行
max_concurrent_tasks = 5
semaphore = Semaphore(max_concurrent_tasks)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:all')
def celery_transfer_entry(self, task_json):
    """
    转移任务入口
    """
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "transfer task: start"})
    task_info = schemas.TransferTaskPublic(**task_json)
    # 获取 source 文件夹下所有顶层文件/文件夹
    dirs = os.listdir(task_info.source_folder)

    task_group = group(celery_transfer_group.s(task_json, os.path.join(
        task_info.source_folder, single_folder)) for single_folder in dirs)
    result = task_group.apply()

    # if task_info.clean_others:
    #     for donefile in done_list:
    #         if donefile in old_list:
    #             old_list.remove(donefile)
    #         else:
    #             os.remove(donefile)
    #     if os.path.isdir(full_path):
    #         cleanExtraMedia(full_path)
    #         cleanFolderWithoutSuffix(full_path, video_type)

    return result


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:group')
def celery_transfer_group(self, task_json, full_path):
    """
    对 group/folder 内所有关联文件进行转移
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
            old_list = findAllVideos(task_info.output_folder, '', [], 2)
        else:
            waiting_list = []
            tf = FileInfo(full_path)
            midfolder = tf.realfolder.replace(task_info.source_folder, '').lstrip("\\").lstrip("/")
            tf.updateMidFolder(midfolder)
            if tf.topfolder != '.':
                tf.parse()
            waiting_list.append(tf)
            old_list = []

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
                else:
                    logger.debug(f"[-] start transfer")
                    # 开始转移
                    destpath = transferfile(currentfile, task_info.source_folder, simplify_tag=task_info.optimize_name,
                                            fixseries_tag=fixseries, dest_folder=task_info.output_folder,
                                            movie_list=waiting_list, linktype=task_info.transfer_type)
                    done_list.append(destpath)
                    # 执行数据库操作
                    record.destpath = destpath
                    record.updatetime = datetime.datetime.now()
        except Exception as e:
            logger.error(e)
        finally:
            session.commit()
            session.close()

        logger.info(f"transfer group end {full_path}")
        return done_list


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='scraping:single')
def celery_scrapping(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "scraping task: start"})
