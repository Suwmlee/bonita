
from celery import shared_task
from app import schemas


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='transfer:shared')
def celery_transfer(self, task_json):
    self.update_state(state="PROGRESS", meta={"progress": 0, "step": "transfer task: start"})
    task_info = schemas.TransferTaskPublic(**task_json)
    print("app_task end")
    data = True
    return data
