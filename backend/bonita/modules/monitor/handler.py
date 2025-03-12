
from typing import Callable
from watchdog.events import FileSystemEventHandler


class MonitorHandler(FileSystemEventHandler):
    """File system event handler that monitors file changes and triggers corresponding tasks"""

    def __init__(self, callback_func: Callable, task_id: str):
        """
        Initialize the file system monitor handler

        Args:
            callback_func: The callback function to execute when events occur
            task_id: The task identifier
        """
        super().__init__()
        self.task_func = callback_func
        self.task_id = task_id

    def on_created(self, event) -> None:
        """Handle file creation events"""
        self.task_func(event, self.task_id, event.src_path)

    def on_moved(self, event) -> None:
        """Handle file move events"""
        self.task_func(event, self.task_id, event.dest_path)

    def on_deleted(self, event) -> None:
        """Handle file deletion events"""
        self.task_func(event, self.task_id, event.src_path)
