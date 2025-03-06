
import logging
from watchdog.events import FileSystemEventHandler

from bonita.db import SessionFactory
from bonita.db.models.task import TransferConfig

logger = logging.getLogger(__name__)


class WatcherHandler(FileSystemEventHandler):
    def __init__(self, task_func, task_id):
        super().__init__()
        self.task_func = task_func
        self.task_id = task_id

    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"on created: {event.src_path}, task_id: {self.task_id}")

    def on_modified(self, event):
        if not event.is_directory:
            logger.info(f"on modified: {event.src_path}, task_id: {self.task_id}")
            try:
                session = SessionFactory()
                task_info = session.query(TransferConfig).filter(TransferConfig.id == self.task_id).first()
                self.task_func(task_info.to_dict(), event.src_path)
            except Exception as e:
                logger.error(f"[!] Watcher created error: {e}")
            finally:
                session.close()

    def on_deleted(self, event):
        if not event.is_directory:
            logger.info(f"on deleted: {event.src_path}, task_id: {self.task_id}")

    def on_moved(self, event):
        if not event.is_directory:
            logger.info(f"on moved: {event.src_path} -> {event.dest_path}, task_id: {self.task_id}")
            self.task_func(self.task_id, event.src_path)
