import logging
import os
import time
from typing import Any

from celery import Celery, Task
from celery.signals import (
    after_setup_logger,
    after_setup_task_logger,
    after_task_publish,
    task_postrun,
    task_prerun,
    task_received,
)
from celery.worker.request import Request

# load tasks
from bonita.celery_tasks import tasks
from bonita.core.config import settings
from bonita.utils.logger import init_log_config, task_id_ctx

logger = logging.getLogger(__name__)


@after_setup_logger.connect
def setup_worker_logger(logger, *args, **kwargs):
    logger.setLevel(settings.LOGGING_LEVEL)


@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    logger.setLevel(settings.LOGGING_LEVEL)


TASK_START_TIME_MAP = {}


@after_task_publish.connect
def task_send_cb(sender: str | None = None, headers: dict | None = None, body: tuple | None = None, **kwargs: Any) -> None:
    info = headers if "task" in headers else body
    logger.info(f"TASK_SENT: {info.get('id')} - {info.get('task')}")


@task_prerun.connect
def task_prerun_cb(task_id: str, task: Task, args: tuple, kwargs: dict, **options: Any) -> None:
    token = task_id_ctx.set(task_id)
    TASK_START_TIME_MAP[task_id] = (time.time(), token)
    logger.info(f"TASK_RUN_STARTED: {task_id} - {task.name}")


@task_postrun.connect
def task_postrun_cb(task_id: str, task: Task, args: tuple, kwargs: dict, retval: Any, state: str, **options: Any) -> None:
    start_time, token = TASK_START_TIME_MAP.pop(
        task_id, (None, None)
    )
    if start_time is not None:
        duration = time.time() - start_time
        logger.info(
            f"TASK_RUN_COMPLETED: {task_id} - {task.name} - Duration: {duration:.2f} seconds"
        )
        if token:
            task_id_ctx.reset(token)


@task_received.connect
def task_received_cb(request: Request, **options: Any) -> None:
    """
    worker接收到task时的回调
    """
    logger.info(f"TASK_RECEIVED: {request.id} - {request.task}")


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
    # celery.conf.update(worker_log_format=settings.LOGGING_FORMAT)
    # celery.conf.update(worker_task_log_format=settings.LOGGING_FORMAT)
    # celery.conf.update(worker_logfile=settings.LOGGING_LOCATION)
    celery.conf.update(
        worker_hijack_root_logger=False
    )  # 禁止 Celery 劫持根日志记录器，保持我们自定义的日志配置生效
    init_log_config()  # 初始化日志配置

    # Set up scheduled tasks
    celery.conf.beat_schedule = {
        # Sync watch history from all sources daily
        "sync-watch-history-daily": {
            "task": "watch_history:sync",
            "schedule": 86400.0,  # 24 hours in seconds
            "args": (None, 30, 100),  # sources=None, days=30, limit=100
        },
    }

    return celery


celery = create_celery()
