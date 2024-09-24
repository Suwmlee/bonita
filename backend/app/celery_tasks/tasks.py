
from celery import shared_task
from app import schemas

from app.celery_tasks.transfer import transfer

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:all')
def celery_transfer(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "transfer task: start"})
    task_info = schemas.TransferTaskPublic(**task_json)

    # 此处进行文件夹级别区分
    # 然后将实际转移，传递给 transfer

    # 开始转移
    transfer(task_info.source_folder, task_info.output_folder,
             task_info.transfer_type, "", ""
             )
    print("app_task end")
    data = True
    return data
