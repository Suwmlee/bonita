from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy.orm import Session

from bonita.db.models.task import CeleryTask
from bonita.core.enums import TaskStatusEnum
from bonita.db import SessionFactory


logger = logging.getLogger(__name__)


class CeleryTaskService:
    """Celery任务管理服务"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionFactory()
        self._should_close_session = session is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session:
            self.session.close()

    def create_task(self, task_id: str, task_type: str) -> CeleryTask:
        """创建新任务记录"""
        task = CeleryTask(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatusEnum.PENDING,
            progress=0.0,
        )
        self.session.add(task)
        self.session.commit()
        return task

    def update_task_progress(self, task_id: str, progress: float, step: str = "", status: TaskStatusEnum = TaskStatusEnum.PROGRESS) -> Optional[CeleryTask]:
        """更新任务进度"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.progress = progress
            task.step = step
            task.status = status
            self.session.commit()
        return task

    def update_task_detail(self, task_id: str, detail: str) -> Optional[CeleryTask]:
        """更新任务详情"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.detail = detail
            self.session.commit()
        return task

    def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None, status: TaskStatusEnum = TaskStatusEnum.SUCCESS) -> Optional[CeleryTask]:
        """完成任务"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.status = status
            task.progress = 100.0 if status == TaskStatusEnum.SUCCESS else task.progress
            if result:
                task.result = str(result)
            self.session.commit()
        return task

    def fail_task(self, task_id: str, error_message: str) -> Optional[CeleryTask]:
        """标记任务失败"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.status = TaskStatusEnum.FAILURE
            task.error_message = error_message
            self.session.commit()
        return task

    def revoke_task(self, task_id: str) -> Optional[CeleryTask]:
        """撤销任务"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.status = TaskStatusEnum.REVOKED
            self.session.commit()
        return task

    def get_task(self, task_id: str) -> Optional[CeleryTask]:
        """获取任务信息"""
        return self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()

    def get_active_tasks(self) -> List[CeleryTask]:
        """获取活跃的任务(进行中的任务)"""
        return self.session.query(CeleryTask).filter(
            CeleryTask.status.in_([TaskStatusEnum.PENDING, TaskStatusEnum.PROGRESS])
        ).order_by(CeleryTask.created_at.desc()).all()

    def get_all_tasks(self, limit: int = 100, offset: int = 0) -> List[CeleryTask]:
        """获取所有任务"""
        return self.session.query(CeleryTask).order_by(
            CeleryTask.created_at.desc()
        ).offset(offset).limit(limit).all()

    def fail_active_tasks(self, error_message: str = "被清理为失败") -> int:
        """
        将当前处于等待或进行中的任务批量标记为失败。

        返回受影响的任务数量。
        """
        updated_count = self.session.query(CeleryTask).filter(
            CeleryTask.status.in_([TaskStatusEnum.PENDING, TaskStatusEnum.PROGRESS])
        ).update({
            CeleryTask.status: TaskStatusEnum.FAILURE,
            CeleryTask.error_message: error_message,
            CeleryTask.updatetime: datetime.now(),
        }, synchronize_session=False)
        self.session.commit()
        return updated_count

    def delete_old_tasks(self, days: int = 30) -> int:
        """删除旧任务记录"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = self.session.query(CeleryTask).filter(
            CeleryTask.created_at < cutoff_date,
            CeleryTask.status.in_([TaskStatusEnum.SUCCESS, TaskStatusEnum.FAILURE, TaskStatusEnum.REVOKED])
        ).delete()
        self.session.commit()
        return deleted_count

    @staticmethod
    def update_progress(task_id: str, progress: float, step: str = ""):
        """
        更新任务进度的便捷函数
        """
        try:
            with CeleryTaskService() as task_service:
                task_service.update_task_progress(task_id, progress, step)
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")

    @staticmethod
    def update_detail(task_id: str, detail: str):
        """更新任务详情"""
        try:
            with CeleryTaskService() as task_service:
                task_service.update_task_detail(task_id, detail)
        except Exception as e:
            logger.error(f"Failed to update task detail: {e}")


class TaskProgressTracker:
    """
    任务进度跟踪器
    """

    def __init__(self, task_id: str, total_steps: int = 100):
        self.task_id = task_id
        self.total_steps = total_steps
        self.current_step = 0

    def update(self, step: str, increment: int = 1):
        """更新进度"""
        self.current_step += increment
        progress = min((self.current_step / self.total_steps) * 100, 100)
        CeleryTaskService.update_progress(self.task_id, progress, step)

    def set_progress(self, progress: float, step: str):
        """直接设置进度"""
        CeleryTaskService.update_progress(self.task_id, progress, step)

    def complete(self, step: str = "任务完成"):
        """完成任务"""
        CeleryTaskService.update_progress(self.task_id, 100.0, step)

    def update_detail(self, detail: str):
        """更新任务路径"""
        CeleryTaskService.update_detail(self.task_id, detail)
