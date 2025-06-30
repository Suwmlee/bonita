from functools import wraps
from typing import Callable
import logging

from bonita.services.celery_service import CeleryTaskService


logger = logging.getLogger(__name__)


def manage_celery_task(task_type: str):
    """
    Celery任务管理装饰器
    自动创建任务记录、更新进度、处理异常
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            task_id = self.request.id

            # 创建任务记录
            with CeleryTaskService() as task_service:
                task_service.create_task(task_id, task_type)

            try:
                # 执行原始任务
                result = func(self, *args, **kwargs)

                # 标记任务完成
                with CeleryTaskService() as task_service:
                    task_service.complete_task(task_id, result={'data': result})

                return result

            except Exception as e:
                # 标记任务失败
                error_message = str(e)
                logger.error(f"Task {task_id} failed: {error_message}")

                with CeleryTaskService() as task_service:
                    task_service.fail_task(task_id, error_message)

        return wrapper
    return decorator
