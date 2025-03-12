
import logging
from datetime import datetime
from threading import Lock
from pathlib import Path
from typing import Dict
from watchdog.events import FileSystemEvent
from watchdog.observers import Observer, ObserverType

from bonita.db import SessionFactory
from bonita.db.models.record import TransRecords
from bonita.db.models.task import TransferConfig
from bonita.utils.filehelper import is_video_file
from bonita.utils.singleton import Singleton
from bonita.modules.monitor.handler import MonitorHandler
from bonita.celery_tasks.tasks import celery_transfer_group

logger = logging.getLogger(__name__)


class MonitorService(metaclass=Singleton):
    """
    File monitoring service that integrates with FastAPI lifecycle events.
    """

    def __init__(self):
        self._monitors: Dict[str, Dict[str, ObserverType]] = {}
        self._is_running: bool = False
        self._lock = Lock()

    def start(self) -> None:
        """Start the monitoring service - can be called from FastAPI startup event"""
        with self._lock:
            if self._is_running:
                logger.warning("MonitorService is already running")
                return
            self._is_running = True
        logger.info("MonitorService started")
        self._load_monitoring_config()

    def stop(self) -> None:
        """Stop the monitoring service - can be called from FastAPI shutdown event"""
        if not self._is_running:
            return

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
                        self.start_monitoring_directory(task_config.source_folder, task_config.id)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")

    def start_monitoring_directory(self, folder_path: str, task_id: str) -> None:
        """Add a directory to monitor for a specific task"""
        if not self._is_running:
            logger.warning("Cannot add directory - MonitorService is not running")
            return

        if not Path(folder_path).is_dir():
            logger.error(f"Directory not found: {folder_path}")
            return

        if folder_path not in self._monitors:
            self._monitors[folder_path] = {}

        if task_id in self._monitors[folder_path]:
            logger.debug(f"Task {task_id} is already monitoring {folder_path}")
            return

        event_handler = MonitorHandler(callback_func=self.handle_file_event, task_id=task_id)
        observer = Observer()
        observer.schedule(event_handler, folder_path, recursive=True)
        observer.start()

        self._monitors[folder_path][task_id] = observer
        logger.info(f"Added monitoring for {folder_path} with task {task_id}")

    def stop_monitoring_directory(self, folder_path: str, task_id: str) -> None:
        """Remove a directory from monitoring for a specific task"""
        if not self._is_running:
            logger.warning("Cannot remove directory - MonitorService is not running")
            return

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

    def handle_file_event(self, event: FileSystemEvent, task_id: str, filepath: str) -> None:
        """Execute task based on file system event"""
        try:
            logger.info(f"File event: {event.event_type}, filepath: {filepath}, task_id: {task_id}")
            if event.event_type == 'created' or event.event_type == 'moved':
                if event.is_directory or not is_video_file(filepath):
                    return
                self._trigger_transfer_task(filepath, task_id)
            elif event.event_type == 'deleted':
                self._update_deleted_records(filepath)
        except Exception as e:
            logger.error(f"Task execution failed: {e}")

    def _trigger_transfer_task(self, filepath: str, task_id: str) -> None:
        """Execute the task's main logic"""
        try:
            logger.info(f"Trigger task for file: {filepath}, task_id: {task_id}")
            with SessionFactory() as session:
                task_info = session.query(TransferConfig).filter(TransferConfig.id == task_id).first()
                if task_info:
                    celery_transfer_group(task_info.to_dict(), filepath, True)
                else:
                    logger.warning(f"No task config found for task_id: {task_id}")
        except Exception as e:
            logger.error(f"Task execution failed: {e}")

    def _update_deleted_records(self, path: str) -> None:
        """Update records for deleted files"""
        try:
            with SessionFactory() as session:
                records = session.query(TransRecords).filter(TransRecords.srcpath.like(f"%{path}%")).all()
                for record in records:
                    logger.info(f"Updating deleted record: {record.srcpath}")
                    record.srcdeleted = True
                    record.updatetime = datetime.now()
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update deleted record: {e}")
