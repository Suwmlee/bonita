
import os
import logging
from celery import shared_task, group
from multiprocessing import Semaphore


from app import schemas
from app.celery_tasks.transfer import transfer

# 创建信号量，最多允许 5 个任务同时执行
max_concurrent_tasks = 5
semaphore = Semaphore(max_concurrent_tasks)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:all')
def celery_transfer_entry(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "transfer task: start"})
    task_info = schemas.TransferTaskPublic(**task_json)

    dirs = os.listdir(task_info.source_folder)

    task_group = group(celery_transfer_group.s(task_json, single_folder) for single_folder in dirs)
    result = task_group.apply_async()
    return result


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:group')
def celery_transfer_group(self, task_json, path):
    with semaphore:
        self.update_state(state="PROGRESS", meta={"progress": 0, "step": "celery_transfer_pool: start"})
        logger.info(f"transfer group start {path}")
        task_info = schemas.TransferTaskPublic(**task_json)
        fixseries = False
        if task_info.content_type == 2:
            fixseries = True

        # 开始转移
        transfer(task_info.source_folder, task_info.output_folder,
                 task_info.transfer_type, "", specified_files=path, fixseries_tag=fixseries
                 )
        # 记录
        logger.info(f"transfer group end {path}")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='scraping:single')
def celery_scrapping(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "scraping task: start"})
