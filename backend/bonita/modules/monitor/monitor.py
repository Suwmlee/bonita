import logging
import os
import time
from datetime import datetime, timedelta
from threading import Lock
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple
from watchdog.events import FileSystemEvent
from watchdog.observers import Observer, ObserverType

from bonita.core.config import settings
from bonita.db import SessionFactory
from bonita.db.models.record import TransRecords
from bonita.db.models.task import TransferConfig
from bonita.utils.filehelper import is_incomplete_download, is_video_file
from bonita.utils.singleton import Singleton
from bonita.modules.monitor.event_handler import FileEventHandler
from bonita.modules.monitor.inbox import EventInbox
from bonita.modules.monitor.polling_handler import PollingHandler
from bonita.tasks import celery_transfer_group

logger = logging.getLogger(__name__)

# 同一文件投递后的短窗口去重，挡住 delay() 与落库之间的 modified 风暴
_ENQUEUE_TTL = 15.0


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
        self._queued: Dict[Tuple[str, str], float] = {}
        self._inbox: Optional[EventInbox] = None

        self._use_polling = settings.MONITOR_USE_POLLING
        self._polling_interval = settings.MONITOR_POLLING_INTERVAL
        self._polling_handler: Optional[PollingHandler] = None

        if self._use_polling:
            logger.info(f"MonitorService will use POLLING mode (interval: {self._polling_interval}s)")
            self._polling_handler = PollingHandler(polling_interval=self._polling_interval)
        else:
            logger.info("MonitorService will use EVENT-BASED mode (watchdog)")
            self._inbox = EventInbox(callback=self.handle_file_event)

    def start(self) -> None:
        """Start the monitoring service - can be called from FastAPI startup event"""
        with self._lock:
            if self._is_running:
                logger.warning("MonitorService is already running")
                return
            self._is_running = True

        if self._use_polling:
            self._polling_handler.start()
        else:
            self._inbox.start()
            logger.info("MonitorService started (event-based)")

        self._load_monitoring_config()

    def stop(self) -> None:
        """Stop the monitoring service - can be called from FastAPI shutdown event"""
        if not self._is_running:
            return

        if self._use_polling:
            self._polling_handler.stop()
        else:
            if self._inbox:
                self._inbox.stop()
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
            self._polling_handler.start_monitoring_directory(
                folder_path,
                task_id,
                folder_type,
                callback_func=self.handle_file_event
            )
            return

        if not Path(folder_path).is_dir():
            logger.error(f"Directory not found: {folder_path}")
            return

        if folder_path not in self._monitors:
            self._monitors[folder_path] = {}

        if task_id in self._monitors[folder_path]:
            logger.debug(f"Task {task_id} is already monitoring {folder_path}")
            return

        event_handler = FileEventHandler(
            callback_func=self.on_watch_event,
            task_id=task_id,
            folder_type=folder_type,
        )
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
            self._polling_handler.stop_monitoring_directory(folder_path, task_id)
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

    def on_watch_event(
        self,
        event: FileSystemEvent,
        task_id: str,
        filepath: str,
        folder_type: Literal["source", "output"],
    ) -> None:
        """watchdog 线程只入队，不查库、不投递。"""
        if event.event_type == "deleted":
            if self._inbox:
                self._inbox.cancel(filepath, task_id)
            self.handle_file_event(event, task_id, filepath, folder_type)
            return

        if folder_type == "output":
            self.handle_file_event(event, task_id, filepath, folder_type)
            return

        if not self._inbox:
            self.handle_file_event(event, task_id, filepath, folder_type)
            return

        if event.event_type == "moved" and getattr(event, "src_path", None):
            self._inbox.cancel(event.src_path, task_id)

        if event.is_directory:
            if event.event_type in ("created", "moved"):
                self._inbox.submit_directory(task_id, filepath, folder_type)
            return

        self._inbox.submit_file(task_id, filepath, folder_type)

    def handle_file_event(self, event: FileSystemEvent, task_id: str, filepath: str, folder_type: Literal["source", "output"]) -> bool:
        """处理已稳定（或删除）的文件系统事件。False 表示失败，调用方可稍后重试。"""
        try:
            if event.event_type == "deleted":
                if folder_type == "source":
                    return self._update_deleted_records(filepath)
                return self._update_output_deleted_records(filepath)

            if event.is_directory:
                return True

            if is_incomplete_download(filepath) or not is_video_file(filepath):
                return True

            if folder_type == "source":
                return self._trigger_transfer_task(filepath, task_id)
            if event.event_type in ("created", "moved"):
                return self._handle_output_file_created(filepath)
            return True
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return False

    def _is_recently_queued(self, task_id: str, filepath: str) -> bool:
        key = (str(task_id), filepath)
        now = time.monotonic()
        with self._lock:
            expired = [k for k, ts in self._queued.items() if now - ts >= _ENQUEUE_TTL]
            for k in expired:
                self._queued.pop(k, None)
            last = self._queued.get(key)
            return last is not None and now - last < _ENQUEUE_TTL

    def _mark_queued(self, task_id: str, filepath: str) -> None:
        with self._lock:
            self._queued[(str(task_id), filepath)] = time.monotonic()

    def _trigger_transfer_task(self, filepath: str, task_id: str) -> bool:
        """
        已忽略 / 已成功 → 跳过；
        失败记录可再试；
        体积不足跳过且不写记录；
        其余投递转移任务。
        """
        try:
            with SessionFactory() as session:
                task_info = session.query(TransferConfig).filter(TransferConfig.id == task_id).first()
                if not task_info:
                    logger.warning(f"No task config found for task_id: {task_id}")
                    return True

                record = session.query(TransRecords).filter(TransRecords.srcpath == filepath).first()
                if record:
                    if record.ignored:
                        logger.info(f"  ⊘ 记录已忽略，跳过: {filepath}")
                        return True
                    if record.success:
                        return True
                    if record.success is None:
                        return True
                    logger.info(f"  ↻ 上次转移失败，重新尝试: {filepath}")

                filename = os.path.basename(filepath)

                if task_info.escape_folder:
                    escape_folders = {fo.strip() for fo in task_info.escape_folder.split(',') if fo.strip()}
                    try:
                        relative = Path(filepath).relative_to(task_info.source_folder)
                        top_dir = relative.parts[0] if len(relative.parts) > 1 else None
                        if top_dir and top_dir in escape_folders:
                            logger.info(f"  ⊘ 文件在排除文件夹 [{top_dir}] 中，跳过: {filepath}")
                            return True
                    except ValueError:
                        pass

                if task_info.escape_literals:
                    escape_lits = [lit.strip() for lit in task_info.escape_literals.split(',') if lit.strip()]
                    if any(lit in filename for lit in escape_lits):
                        logger.info(f"  ⊘ 文件名包含排除文字，跳过: {filepath}")
                        return True

                if task_info.escape_size and task_info.escape_size > 0:
                    try:
                        filesize = os.path.getsize(filepath)
                    except OSError as e:
                        logger.warning(f"  ⊘ 无法读取文件大小，稍后重试: {filepath} ({e})")
                        return False
                    if filesize < task_info.escape_size * 1024 * 1024:
                        logger.info(f"  ⊘ 文件小于 {task_info.escape_size}MB，跳过: {filepath}")
                        return True

                if self._is_recently_queued(task_id, filepath):
                    return True

                logger.info(f"Trigger task for file: {filepath}, task_id: {task_id}")
                if not celery_transfer_group.app.conf.broker_url:
                    celery_transfer_group.app.conf.broker_url = settings.CELERY_BROKER_URL
                    logger.info(f"Set broker_url to: {celery_transfer_group.app.conf.broker_url}")
                celery_transfer_group.delay(task_info.to_dict(), filepath, True)
                self._mark_queued(task_id, filepath)
                return True
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return False

    def _update_deleted_records(self, path: str) -> bool:
        """Update records for deleted files in source folder"""
        try:
            with SessionFactory() as session:
                records = session.query(TransRecords).filter(TransRecords.srcpath.startswith(path)).all()
                for record in records:
                    logger.info(f"Updating deleted source record: {record.srcpath}")
                    record.srcdeleted = True
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update deleted record: {e}")
            return False

    def _handle_output_file_created(self, filepath: str) -> bool:
        """处理输出文件夹中文件创建的逻辑"""
        try:
            with SessionFactory() as session:
                record = session.query(TransRecords).filter(TransRecords.destpath == filepath).first()
                if record and record.deadtime:
                    logger.info(f"Clearing deadtime for record: {record.destpath}")
                    record.deadtime = None
                    record.deleted = False
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to handle output file created: {e}")
            return False

    def _update_output_deleted_records(self, path: str) -> bool:
        """处理输出文件夹中文件删除的逻辑，更新deadtime"""
        try:
            with SessionFactory() as session:
                records = session.query(TransRecords).filter(TransRecords.destpath.startswith(path)).all()
                for record in records:
                    logger.info(f"Setting deadtime for record: {record.destpath}")
                    record.deadtime = datetime.now() + timedelta(days=7)
                    record.deleted = True
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update output deleted record: {e}")
            return False
