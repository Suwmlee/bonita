import time
import json

from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},
             name='transfer:shared')
def celery_run_task(self, task):
    print("app_task start")
    time.sleep(int(task))
    print("app_task end")
    data = True
    return json.dumps(data)
