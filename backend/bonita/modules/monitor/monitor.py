import logging
from datetime import datetime, timedelta
from threading import Lock
from pathlib import Path
from typing import Dict, Literal, Optional
from watchdog.events import FileSystemEvent
from watchdog.observers import Observer, ObserverType

from bonita.core.config import settings
from bonita.db import SessionFactory
from bonita.db.models.record import TransRecords
from bonita.db.models.task import TransferConfig
from bonita.utils.filehelper import is_video_file
from bonita.utils.singleton import Singleton
from bonita.modules.monitor.event_handler import FileEventHandler
from bonita.modules.monitor.polling_handler import PollingHandler
from bonita.celery_tasks.tasks import celery_transfer_group

logger = logging.getLogger(__name__)


class MonitorService(metaclass=Singleton):
    """
    File monitoring service that integrates with FastAPI lifecycle events.
    Supports both event-based (watchdog) and polling-based monitoring.

    For SMB/CIFS network drives, use polling mode by setting:
    MONITOR_USE_POLLING=true in environment or settings
    """

    def __init__(self):
        self._monitors: Dict[str, Dict[str, ObserverType]] = {}
        self._is_running: bool = False
        self._lock = Lock()

        # 检查是否使用轮询模式（适用于网络挂载文件夹）
        self._use_polling = getattr(settings, 'MONITOR_USE_POLLING', True)
        self._polling_interval = getattr(settings, 'MONITOR_POLLING_INTERVAL', 10)
        self._polling_handler: Optional[PollingHandler] = None

        if self._use_polling:
            logger.info(f"MonitorService will use POLLING mode (interval: {self._polling_interval}s)")
            self._polling_handler = PollingHandler(polling_interval=self._polling_interval)
        else:
            logger.info("MonitorService will use EVENT-BASED mode (watchdog)")

    def start(self) -> None:
        """Start the monitoring service - can be called from FastAPI startup event"""
        with self._lock:
            if self._is_running:
                logger.warning("MonitorService is already running")
                return
            self._is_running = True

        if self._use_polling:
            # 使用轮询模式
            self._polling_handler.start()
        else:
            # 使用事件监听模式
            logger.info("MonitorService started (event-based)")

        # 统一加载监控配置
        self._load_monitoring_config()

    def stop(self) -> None:
        """Stop the monitoring service - can be called from FastAPI shutdown event"""
        if not self._is_running:
            return

        if self._use_polling:
            # 停止轮询服务
            self._polling_handler.stop()
        else:
            # 停止事件监听服务
            for folder_path in list(self._monitors.keys()):
                for task_id in list(self._monitors[folder_path].keys()):
                    self._stop_monitoring(folder_path, task_id)

        self._is_running = False
        logger.info("MonitorService stopped")

    def _load_monitoring_config(self) -> None:
        """Load monitoring configuration from database"""
        try:
            with SessionFactory() as session:
                task_configs = session.query(TransferConfig).all()
                for task_config in task_configs:
                    if task_config.auto_watch:
                        logger.info(f"Setting up monitoring for task: {task_config.id}")
                        self.start_monitoring_directory(task_config.source_folder, task_config.id, "source")
                        self.start_monitoring_directory(task_config.output_folder, task_config.id, "output")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")

    def start_monitoring_directory(self, folder_path: str, task_id: str, folder_type: Literal["source", "output"]) -> None:
        """Add a directory to monitor for a specific task with folder type"""
        if not self._is_running:
            logger.warning("Cannot add directory - MonitorService is not running")
            return

        if self._use_polling:
            # 使用轮询模式，传递回调函数
            self._polling_handler.start_monitoring_directory(
                folder_path,
                task_id,
                folder_type,
                callback_func=self.handle_file_event
            )
            return

        # 使用事件监听模式
        if not Path(folder_path).is_dir():
            logger.error(f"Directory not found: {folder_path}")
            return

        if folder_path not in self._monitors:
            self._monitors[folder_path] = {}

        if task_id in self._monitors[folder_path]:
            logger.debug(f"Task {task_id} is already monitoring {folder_path}")
            return

        event_handler = FileEventHandler(callback_func=self.handle_file_event, task_id=task_id, folder_type=folder_type)
        observer = Observer()
        observer.schedule(event_handler, folder_path, recursive=True)
        observer.start()

        self._monitors[folder_path][task_id] = observer
        logger.info(f"Added monitoring for {folder_path} with task {task_id} as {folder_type} folder")

    def stop_monitoring_directory(self, folder_path: str, task_id: str) -> None:
        """Remove a directory from monitoring for a specific task"""
        if not self._is_running:
            logger.warning("Cannot remove directory - MonitorService is not running")
            return

        if self._use_polling:
            # 使用轮询模式
            self._polling_handler.stop_monitoring_directory(folder_path, task_id)
            return

        # 使用事件监听模式
        self._stop_monitoring(folder_path, task_id)

    def _stop_monitoring(self, folder_path: str, task_id: str) -> None:
        """Stop an observer and clean up"""
        if folder_path in self._monitors and task_id in self._monitors[folder_path]:
            observer = self._monitors[folder_path].pop(task_id)
            observer.stop()
            observer.join()
            logger.info(f"Stopped monitoring {folder_path} for task {task_id}")

            if not self._monitors[folder_path]:
                del self._monitors[folder_path]

    def handle_file_event(self, event: FileSystemEvent, task_id: str, filepath: str, folder_type: Literal["source", "output"]) -> None:
        """Execute task based on file system event"""
        try:
            logger.info(
                f"File event: {event.event_type}, filepath: {filepath}, task_id: {task_id}, type: {folder_type}")
            if folder_type == "source":
                # 源文件夹的处理逻辑
                if event.event_type == 'created' or event.event_type == 'moved':
                    if event.is_directory or not is_video_file(filepath):
                        return
                    self._trigger_transfer_task(filepath, task_id)
                elif event.event_type == 'deleted':
                    self._update_deleted_records(filepath)
            elif folder_type == "output":
                # 输出文件夹的处理逻辑
                if event.event_type == 'created' or event.event_type == 'moved':
                    if event.is_directory or not is_video_file(filepath):
                        return
                    self._handle_output_file_created(filepath)
                elif event.event_type == 'deleted':
                    self._update_output_deleted_records(filepath)
        except Exception as e:
            logger.error(f"Task execution failed: {e}")

    def _trigger_transfer_task(self, filepath: str, task_id: str) -> None:
        """Execute the task's main logic"""
        try:
            logger.info(f"Trigger task for file: {filepath}, task_id: {task_id}")
            with SessionFactory() as session:
                task_info = session.query(TransferConfig).filter(TransferConfig.id == task_id).first()
                if task_info:
                    # TODO: 环境不同可能存在丢失情况...
                    if not celery_transfer_group.app.conf.broker_url:
                        celery_transfer_group.app.conf.broker_url = settings.CELERY_BROKER_URL
                        logger.info(f"Set broker_url to: {celery_transfer_group.app.conf.broker_url}")
                    celery_transfer_group.delay(task_info.to_dict(), filepath, True)
                else:
                    logger.warning(f"No task config found for task_id: {task_id}")
        except Exception as e:
            logger.error(f"Task execution failed: {e}")

    def _update_deleted_records(self, path: str) -> None:
        """Update records for deleted files in source folder"""
        try:
            with SessionFactory() as session:
                # 删除可能是文件夹
                records = session.query(TransRecords).filter(TransRecords.srcpath.startswith(path)).all()
                for record in records:
                    logger.info(f"Updating deleted source record: {record.srcpath}")
                    record.srcdeleted = True
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update deleted record: {e}")

    def _handle_output_file_created(self, filepath: str) -> None:
        """处理输出文件夹中文件创建的逻辑"""
        try:
            with SessionFactory() as session:
                # 查找是否有对应的记录且有deadtime值
                record = session.query(TransRecords).filter(TransRecords.destpath == filepath).first()
                if record:
                    if record.deadtime:
                        logger.info(f"Clearing deadtime for record: {record.destpath}")
                        record.deadtime = None
                        record.deleted = False
                session.commit()
        except Exception as e:
            logger.error(f"Failed to handle output file created: {e}")

    def _update_output_deleted_records(self, path: str) -> None:
        """处理输出文件夹中文件删除的逻辑，更新deadtime"""
        try:
            with SessionFactory() as session:
                # 删除可能是文件夹
                records = session.query(TransRecords).filter(TransRecords.destpath.startswith(path)).all()
                for record in records:
                    logger.info(f"Setting deadtime for record: {record.destpath}")
                    record.deadtime = datetime.now() + timedelta(days=7)
                    record.deleted = True
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update output deleted record: {e}")
