import os

from celery import Celery
# load tasks
from bonita.celery_tasks import tasks
from bonita.core.config import settings

def create_celery():
    """
    配置 https://docs.celeryq.dev/en/stable/userguide/configuration.html#general-settings
    """
    celery = Celery("bonita")
    celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", settings.CELERY_BROKER_URL)
    celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", settings.CELERY_RESULT_BACKEND)

    celery.conf.update(timezone="Asia/Shanghai")  # 时区
    celery.conf.update(enable_utc=False)  # 关闭UTC时区。默认启动
    celery.conf.update(task_track_started=True)  # 启动任务跟踪
    celery.conf.update(result_expires=200)  # 结果过期时间，200s
    celery.conf.update(result_persistent=True)
    celery.conf.update(worker_send_task_events=False)
    celery.conf.update(worker_prefetch_multiplier=1)
    celery.conf.update(broker_connection_retry_on_startup=True)  # 启动时重试代理连接

    # Set up scheduled tasks
    celery.conf.beat_schedule = {
        # Sync watch history from all sources daily
        'sync-watch-history-daily': {
            'task': 'watch_history:sync',
            'schedule': 86400.0,  # 24 hours in seconds
            'args': (None, 30, 100),  # sources=None, days=30, limit=100
        },
    }

    return celery


celery = create_celery()
