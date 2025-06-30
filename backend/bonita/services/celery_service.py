from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy.orm import Session

from bonita.db.models.task import CeleryTask
from bonita.core.enums import TaskStatus
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

    def create_task(self, task_id: str, task_name: str) -> CeleryTask:
        """创建新任务记录"""
        task = CeleryTask(
            task_id=task_id,
            task_name=task_name,
            status=TaskStatus.PENDING,
            progress=0.0,
        )
        self.session.add(task)
        self.session.commit()
        return task

    def update_task_progress(self, task_id: str, progress: float, step: str = "", status: TaskStatus = TaskStatus.PROGRESS) -> Optional[CeleryTask]:
        """更新任务进度"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.progress = progress
            task.step = step
            task.status = status
            self.session.commit()
        return task

    def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None, status: TaskStatus = TaskStatus.SUCCESS) -> Optional[CeleryTask]:
        """完成任务"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.status = status
            task.progress = 100.0 if status == TaskStatus.SUCCESS else task.progress
            if result:
                task.result = str(result)
            self.session.commit()
        return task

    def fail_task(self, task_id: str, error_message: str) -> Optional[CeleryTask]:
        """标记任务失败"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.status = TaskStatus.FAILURE
            task.error_message = error_message
            self.session.commit()
        return task

    def revoke_task(self, task_id: str) -> Optional[CeleryTask]:
        """撤销任务"""
        task = self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
        if task:
            task.status = TaskStatus.REVOKED
            self.session.commit()
        return task

    def get_task(self, task_id: str) -> Optional[CeleryTask]:
        """获取任务信息"""
        return self.session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()

    def get_tasks_by_name(self, task_name: str, limit: int = 100) -> List[CeleryTask]:
        """根据任务名称获取任务列表"""
        return self.session.query(CeleryTask).filter(
            CeleryTask.task_name == task_name
        ).order_by(CeleryTask.created_at.desc()).limit(limit).all()

    def get_active_tasks(self) -> List[CeleryTask]:
        """获取活跃的任务(进行中的任务)"""
        return self.session.query(CeleryTask).filter(
            CeleryTask.status.in_([TaskStatus.PENDING, TaskStatus.PROGRESS])
        ).order_by(CeleryTask.created_at.desc()).all()

    def get_all_tasks(self, limit: int = 100, offset: int = 0) -> List[CeleryTask]:
        """获取所有任务"""
        return self.session.query(CeleryTask).order_by(
            CeleryTask.created_at.desc()
        ).offset(offset).limit(limit).all()

    def delete_old_tasks(self, days: int = 30) -> int:
        """删除旧任务记录"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = self.session.query(CeleryTask).filter(
            CeleryTask.created_at < cutoff_date,
            CeleryTask.status.in_([TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED])
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
    def update_step(task_id: str, step: str):
        """
        更新任务步骤的便捷函数
        """
        try:
            with CeleryTaskService() as task_service:
                task = task_service.get_task(task_id)
                if task:
                    task_service.update_task_progress(task_id, task.progress, step)
        except Exception as e:
            logger.error(f"Failed to update task step: {e}")


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
