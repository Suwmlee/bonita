import logging
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Literal, Set, Optional, Callable
from threading import Thread, Lock, Event
from dataclasses import dataclass

from bonita.utils.filehelper import is_video_file
from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)


@dataclass
class PollingFileEvent:
    """模拟文件系统事件，用于回调"""
    event_type: Literal["created", "deleted"]
    src_path: str
    is_directory: bool


@dataclass
class FileSnapshot:
    """文件快照信息"""
    path: str
    size: int
    mtime: float
    is_directory: bool

    def get_hash(self) -> str:
        """生成文件快照的哈希值"""
        content = f"{self.path}:{self.size}:{self.mtime}:{self.is_directory}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class MonitorTask:
    """监控任务配置"""
    task_id: str
    folder_path: str
    folder_type: Literal["source", "output"]
    callback_func: Callable
    last_scan: Optional[datetime] = None
    file_snapshots: Dict[str, FileSnapshot] = None
    
    def __post_init__(self):
        if self.file_snapshots is None:
            self.file_snapshots = {}


class PollingHandler(metaclass=Singleton):
    """
    基于轮询的文件监控服务，适用于 SMB/CIFS 等网络挂载文件夹
    """

    def __init__(self, polling_interval: int = 10):
        """
        初始化轮询监控服务

        Args:
            polling_interval: 轮询间隔（秒），默认 10 秒
        """
        self._monitor_tasks: Dict[str, MonitorTask] = {}  # key: f"{folder_path}:{task_id}"
        self._is_running: bool = False
        self._lock = Lock()
        self._polling_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._polling_interval = polling_interval
        
        # 文件稳定性检查：文件需要连续2次扫描保持不变才认为是稳定的
        self._unstable_files: Dict[str, FileSnapshot] = {}  # 不稳定的文件（正在写入中）

    def start(self) -> None:
        """启动监控服务"""
        with self._lock:
            if self._is_running:
                logger.warning("PollingMonitorService is already running")
                return
            self._is_running = True
            self._stop_event.clear()
        
        logger.info("PollingMonitorService started")
        
        # 启动轮询线程
        self._polling_thread = Thread(target=self._polling_loop, daemon=True)
        self._polling_thread.start()

    def stop(self) -> None:
        """停止监控服务"""
        if not self._is_running:
            return

        logger.info("Stopping PollingMonitorService...")
        self._is_running = False
        self._stop_event.set()

        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=5)

        with self._lock:
            self._monitor_tasks.clear()

        logger.info("PollingMonitorService stopped")

    def start_monitoring_directory(
        self, 
        folder_path: str, 
        task_id: str, 
        folder_type: Literal["source", "output"],
        callback_func: Callable
    ) -> None:
        """添加目录到监控列表"""
        if not self._is_running:
            logger.warning("Cannot add directory - PollingMonitorService is not running")
            return
            
        path = Path(folder_path)
        if not path.exists():
            logger.error(f"Directory not found: {folder_path}")
            return
            
        if not path.is_dir():
            logger.error(f"Path is not a directory: {folder_path}")
            return
            
        key = self._get_task_key(folder_path, task_id)
        
        with self._lock:
            if key in self._monitor_tasks:
                logger.debug(f"Task {task_id} is already monitoring {folder_path}")
                return
                
            monitor_task = MonitorTask(
                task_id=task_id,
                folder_path=folder_path,
                folder_type=folder_type,
                callback_func=callback_func
            )
            
            # 初始化文件快照
            monitor_task.file_snapshots = self._scan_directory(folder_path)
            monitor_task.last_scan = datetime.now()
            
            self._monitor_tasks[key] = monitor_task
            
        logger.info(
            f"Added polling monitor for {folder_path} with task {task_id} as {folder_type} folder "
            f"(found {len(monitor_task.file_snapshots)} files)"
        )

    def stop_monitoring_directory(self, folder_path: str, task_id: str) -> None:
        """停止监控指定目录"""
        key = self._get_task_key(folder_path, task_id)

        with self._lock:
            if key in self._monitor_tasks:
                del self._monitor_tasks[key]
                logger.info(f"Stopped monitoring {folder_path} for task {task_id}")

    def _get_task_key(self, folder_path: str, task_id: str) -> str:
        """生成监控任务的唯一键"""
        return f"{folder_path}:{task_id}"

    def _polling_loop(self) -> None:
        """轮询循环"""
        logger.info(f"Polling loop started with interval: {self._polling_interval}s")

        while self._is_running and not self._stop_event.is_set():
            try:
                self._check_all_directories()
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)

            # 等待下一次轮询
            self._stop_event.wait(timeout=self._polling_interval)

        logger.info("Polling loop stopped")

    def _check_all_directories(self) -> None:
        """检查所有监控的目录"""
        with self._lock:
            tasks = list(self._monitor_tasks.values())

        for task in tasks:
            try:
                self._check_directory(task)
            except Exception as e:
                logger.error(f"Error checking directory {task.folder_path}: {e}", exc_info=True)

    def _check_directory(self, task: MonitorTask) -> None:
        """检查单个目录的变化"""
        current_snapshots = self._scan_directory(task.folder_path)
        old_snapshots = task.file_snapshots
        
        # 检测新增和变化的文件
        for filepath, snapshot in current_snapshots.items():
            if filepath not in old_snapshots:
                # 新文件 - 加入稳定性检查队列
                self._is_file_stable(filepath, snapshot)
            elif filepath in self._unstable_files:
                # 文件在不稳定列表中，继续检查是否已稳定
                if self._is_file_stable(filepath, snapshot):
                    self._handle_file_created(task, snapshot)
        
        # 检测删除的文件
        for filepath in old_snapshots:
            if filepath not in current_snapshots:
                self._handle_file_deleted(task, old_snapshots[filepath])
                # 如果文件在不稳定列表中，也要清理
                if filepath in self._unstable_files:
                    del self._unstable_files[filepath]
        
        # 更新快照
        task.file_snapshots = current_snapshots
        task.last_scan = datetime.now()

    def _scan_directory(self, folder_path: str) -> Dict[str, FileSnapshot]:
        """扫描目录并生成文件快照（仅扫描视频文件）"""
        snapshots = {}
        
        try:
            path = Path(folder_path)
            if not path.exists():
                logger.warning(f"Directory not found during scan: {folder_path}")
                return snapshots
            
            # 递归扫描所有文件
            for item in path.rglob('*'):
                try:
                    # 跳过目录，只处理文件
                    if item.is_dir():
                        continue
                    
                    # 只扫描视频文件
                    if not is_video_file(str(item)):
                        continue
                    
                    stat = item.stat()
                    snapshot = FileSnapshot(
                        path=str(item),
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        is_directory=False  # 已经确定是文件
                    )
                    snapshots[str(item)] = snapshot
                except (OSError, PermissionError) as e:
                    logger.debug(f"Cannot access {item}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scanning directory {folder_path}: {e}")
            
        return snapshots

    def _is_file_stable(self, filepath: str, snapshot: FileSnapshot) -> bool:
        """
        检查文件是否稳定（已完成写入）

        通过比较连续多次扫描，如果文件大小和修改时间保持不变，则认为稳定
        """
        if snapshot.is_directory:
            return True  # 目录总是稳定的

        # 检查是否在不稳定列表中
        if filepath in self._unstable_files:
            old_snapshot = self._unstable_files[filepath]
            if old_snapshot.get_hash() == snapshot.get_hash():
                # 文件在两次扫描间保持不变，认为稳定
                del self._unstable_files[filepath]
                return True
            else:
                # 文件仍在变化，更新快照
                self._unstable_files[filepath] = snapshot
                return False
        else:
            # 首次发现该文件，标记为不稳定
            self._unstable_files[filepath] = snapshot
            return False

    def _handle_file_created(self, task: MonitorTask, snapshot: FileSnapshot) -> None:
        """处理文件创建事件"""
        # 创建事件对象
        event = PollingFileEvent(
            event_type="created",
            src_path=snapshot.path,
            is_directory=snapshot.is_directory
        )
        
        # 调用回调函数
        try:
            task.callback_func(event, task.task_id, snapshot.path, task.folder_type)
        except Exception as e:
            logger.error(f"Callback function failed: {e}", exc_info=True)

    def _handle_file_deleted(self, task: MonitorTask, snapshot: FileSnapshot) -> None:
        """处理文件删除事件"""
        # 创建事件对象
        event = PollingFileEvent(
            event_type="deleted",
            src_path=snapshot.path,
            is_directory=snapshot.is_directory
        )
        
        # 调用回调函数
        try:
            task.callback_func(event, task.task_id, snapshot.path, task.folder_type)
        except Exception as e:
            logger.error(f"Callback function failed: {e}", exc_info=True)
