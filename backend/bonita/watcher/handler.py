import logging
import os
import time
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

    def _wait_for_file_stable(self, filepath: str, interval: int = 6) -> bool:
        """
        等待文件稳定（写入完成）

        Args:
            filepath: 文件路径
            interval: 检查间隔（秒）
        Returns:
            bool: 是否成功等到文件稳定
        """
        last_size = -1
        keep_checking = True
        logger.info(f"[!] Waiting for file {filepath} to stabilize")
        while keep_checking:
            try:
                current_size = os.path.getsize(filepath)
                if current_size == last_size:
                    # 文件大小连续两次相同，假设写入完成
                    logger.info(f"[!] File {filepath} is stable")
                    return True
                last_size = current_size
                time.sleep(interval)
            except OSError as e:
                logger.error(f"[!] Error checking file size: {e}")
                return False

        logger.warning(f"[!] Timeout waiting for file {filepath} to stabilize")
        return False

    def _execute_task(self, filepath: str) -> None:
        """执行任务的主要逻辑"""
        # 等待文件稳定才可以移动，如果是硬链接，不需要等待
        # if not self._wait_for_file_stable(filepath):
        #     return
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
