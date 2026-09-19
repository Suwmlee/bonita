from functools import wraps
from typing import Callable
import logging

from bonita.core.enums import TaskStatusEnum
from bonita.services.celery_service import CeleryTaskService


logger = logging.getLogger(__name__)


def manage_celery_task(task_type: str):
    """写入 CeleryTask 记录；父任务已取消时跳过执行。"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            task_id = self.request.id
            with CeleryTaskService() as task_service:
                task_service.create_task(task_id, task_type)
                if self.request.parent_id:
                    parent = task_service.get_task(self.request.parent_id)
                    if parent and parent.status == TaskStatusEnum.REVOKED:
                        task_service.revoke_task(task_id)
                        logger.info(
                            f"Task {task_id} ({task_type}) skipped: "
                            f"parent {self.request.parent_id} has been revoked"
                        )
                        return []

            try:
                result = func(self, *args, **kwargs)
                with CeleryTaskService() as task_service:
                    task_service.complete_task(task_id, result={'data': result})
                return result
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                with CeleryTaskService() as task_service:
                    task_service.fail_task(task_id, str(e))

        return wrapper
    return decorator
