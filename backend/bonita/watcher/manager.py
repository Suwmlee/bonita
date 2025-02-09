
import time
from threading import Thread
from typing import Dict, List
from watchdog.observers import Observer, ObserverType

# 监控管理类，负责管理多个监控目录
from bonita.celery_tasks.tasks import process_watcher_task
from bonita.watcher.handler import WatcherHandler


class WatcherManager:
    def __init__(self):
        # 存储目录与任务 id 的映射
        self._watchers: Dict[str, Dict[str, ObserverType]] = {}


    def add_directory(self, folder_path: str, task_id: str):
        if folder_path not in self._watchers:
            self._watchers[folder_path] = {}

        if task_id in self._watchers[folder_path]:
            return  # 已经有相同的 id 监控该目录

        event_handler = WatcherHandler(task_func=process_watcher_task, task_id=task_id)
        observer = Observer()
        observer.schedule(event_handler, folder_path, recursive=True)
        observer.start()

        # 启动监控的线程
        thread = Thread(target=self._run_observer, args=(observer,))
        thread.daemon = True
        thread.start()

        self._watchers[folder_path][task_id] = observer

    def remove_directory(self, folder_path: str, task_id: str):
        if folder_path in self._watchers and task_id in self._watchers[folder_path]:
            observer = self._watchers[folder_path].pop(task_id)
            observer.stop()
            observer.join()

            # 如果该目录下没有更多监控任务，删除目录
            if not self._watchers[folder_path]:
                del self._watchers[folder_path]

    def list_directories(self) -> Dict[str, List[str]]:
        """列出当前所有监控的目录及其对应的任务 id"""
        return {folder: list(task_ids.keys()) for folder, task_ids in self._watchers.items()}

    def _run_observer(self, observer):
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


# 初始化监控管理器
watcher_manager = WatcherManager()
