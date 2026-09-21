import logging
from typing import Callable, Literal
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """File system event handler that monitors file changes and triggers corresponding tasks"""

    def __init__(self, callback_func: Callable, task_id: str, folder_type: Literal["source", "output"]):
        super().__init__()
        self.task_func = callback_func
        self.task_id = task_id
        self.folder_type = folder_type

    def on_created(self, event) -> None:
        self._emit(event, event.src_path)

    def on_moved(self, event) -> None:
        self._emit(event, event.dest_path)

    def on_deleted(self, event) -> None:
        self._emit(event, event.src_path)

    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._emit(event, event.src_path)

    def _emit(self, event, filepath: str) -> None:
        # Transmission 删种会先乱码改名再删，created 可能指向已不存在的路径
        try:
            self.task_func(event, self.task_id, filepath, self.folder_type)
        except Exception:
            logger.exception("Monitor callback failed: %s", filepath)
