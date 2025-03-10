import logging
import os
from datetime import datetime
from typing import Callable
from watchdog.events import FileSystemEventHandler

from bonita.db import SessionFactory
from bonita.db.models.task import TransferConfig
from bonita.db.models.record import TransRecords
from bonita.utils.filehelper import video_type

logger = logging.getLogger(__name__)


class WatcherHandler(FileSystemEventHandler):
    """文件系统事件处理器，用于监控文件变化并触发相应任务"""

    def __init__(self, task_func: Callable, task_id: str):
        """
        初始化文件监控处理器

        Args:
            task_func: 任务处理函数
            task_id: 任务标识符
        """
        super().__init__()
        self.task_func = task_func
        self.task_id = task_id

    def _is_video_file(self, filepath: str) -> bool:
        """检查文件是否为视频文件"""
        ext = os.path.splitext(filepath)[1].lower()
        is_video = ext in video_type
        if not is_video:
            logger.debug(f"[!] {filepath} is not a video file")
        return is_video

    def _get_session(self):
        """创建并返回数据库会话"""
        return SessionFactory()

    def _execute_task(self, filepath: str) -> None:
        """执行任务的主要逻辑"""
        session = self._get_session()
        try:
            task_info = session.query(TransferConfig).filter(TransferConfig.id == self.task_id).first()
            if task_info:
                self.task_func(task_info.to_dict(), filepath, True)
            else:
                logger.warning(f"[!] No task config found for task_id: {self.task_id}")
        except Exception as e:
            logger.error(f"[!] Task execution failed: {e}")
        finally:
            session.close()

    def _update_deleted_record(self, path: str) -> None:
        """更新删除文件的记录"""
        session = self._get_session()
        try:
            records = session.query(TransRecords).filter(TransRecords.srcpath.like(f"%{path}%")).all()
            for record in records:
                logger.info(f"[!] update deleted record: {record.srcpath}")
                record.srcdeleted = True
                record.updatetime = datetime.now()
            session.commit()
        except Exception as e:
            logger.error(f"[!] Failed to update deleted record: {e}")
        finally:
            session.close()

    def on_created(self, event) -> None:
        """处理文件创建事件"""
        if event.is_directory or not self._is_video_file(event.src_path):
            return

        logger.info(f"[!] File created: {event.src_path}, task_id: {self.task_id}")
        self._execute_task(event.src_path)
        logger.info(f"[!] File creation processed: {event.src_path}, task_id: {self.task_id}")

    def on_moved(self, event) -> None:
        """处理文件移动事件"""
        if event.is_directory or not self._is_video_file(event.src_path):
            return

        logger.info(f"[!] File moved: {event.src_path} -> {event.dest_path}, task_id: {self.task_id}")
        self._execute_task(event.dest_path)
        logger.info(f"[!] File move processed: {event.dest_path}, task_id: {self.task_id}")

    def on_deleted(self, event) -> None:
        """处理文件删除事件"""
        logger.info(f"[!] File deleted: {event.src_path}, task_id: {self.task_id}")
        self._update_deleted_record(event.src_path)
        logger.info(f"[!] File deletion processed: {event.src_path}, task_id: {self.task_id}")
