import time
from app.worker import celery


@celery.task
def test_app_task(num: int):
    print("app_task start")
    time.sleep(num)
    print("app_task end")
    return True
