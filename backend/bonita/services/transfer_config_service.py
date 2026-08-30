from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from bonita import schemas
from bonita.celery_tasks.tasks import celery_transfer_entry, celery_transfer_group
from bonita.core.enums import TaskStatusEnum
from bonita.db.models.task import TransferConfig
from bonita.modules.monitor.monitor import MonitorService


class TransferConfigService:
    """转移任务配置 CRUD，以及立即执行任务。"""

    def __init__(self, session: Session):
        self.session = session

    def list_configs(self, skip: int = 0, limit: int = 100) -> Tuple[List[TransferConfig], int]:
        task_configs = self.session.query(TransferConfig).offset(skip).limit(limit).all()
        count = self.session.query(TransferConfig).count()
        return task_configs, count

    def get_by_id(self, config_id: int) -> Optional[TransferConfig]:
        return self.session.get(TransferConfig, config_id)

    def _sync_monitor(self, task_config: TransferConfig) -> None:
        if task_config.auto_watch:
            MonitorService().start_monitoring_directory(task_config.source_folder, task_config.id, "source")
            MonitorService().start_monitoring_directory(task_config.output_folder, task_config.id, "output")
        else:
            MonitorService().stop_monitoring_directory(task_config.source_folder, task_config.id)
            MonitorService().stop_monitoring_directory(task_config.output_folder, task_config.id)

    def create_config(self, config_in: schemas.TransferConfigCreate) -> TransferConfig:
        task_config = TransferConfig(**config_in.model_dump())
        task_config.create(self.session)
        self._sync_monitor(task_config)
        return task_config

    def update_config(self, config_id: int, update_dict: dict) -> Optional[TransferConfig]:
        task_config = self.get_by_id(config_id)
        if not task_config:
            return None
        task_config.update(self.session, update_dict)
        self.session.commit()
        self.session.refresh(task_config)
        self._sync_monitor(task_config)
        return task_config

    def delete_config(self, config_id: int) -> Optional[TransferConfig]:
        config = self.get_by_id(config_id)
        if not config:
            return None
        if config.auto_watch:
            MonitorService().stop_monitoring_directory(config.source_folder, config.id)
            MonitorService().stop_monitoring_directory(config.output_folder, config.id)
        self.session.delete(config)
        self.session.commit()
        return config

    def run_transfer(self, config_id: int, path: Optional[str] = None) -> Optional[schemas.TaskStatus]:
        task_conf = self.get_by_id(config_id)
        if not task_conf:
            return None
        task_dict = task_conf.to_dict()
        if path:
            task = celery_transfer_group.delay(task_dict, path.strip(), True)
            task_type = "TransferGroup"
            detail = path.strip()
        else:
            task = celery_transfer_entry.delay(task_dict)
            task_type = "TransferAll"
            detail = str(config_id)
        return schemas.TaskStatus(
            task_id=task.id,
            name=task_conf.name,
            status=TaskStatusEnum.PENDING,
            task_type=task_type,
            detail=detail,
            progress=0.0,
            step="任务已启动",
        )
