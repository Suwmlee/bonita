import logging
import os
import time
from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Callable, Dict, List, Literal, Optional, Tuple

from bonita.utils.filehelper import findAllFilesWithSuffix, is_incomplete_download, is_video_file, video_type

logger = logging.getLogger(__name__)

_TICK = 1.0
_STABLE_DELAY = 2.0
_STABLE_CHECKS = 2
_DIR_RESCAN_DELAYS = (15.0, 60.0)


@dataclass
class MonitorEvent:
    event_type: str
    src_path: str
    is_directory: bool = False


@dataclass
class _FileWait:
    task_id: str
    filepath: str
    folder_type: Literal["source", "output"]
    size: int
    mtime: float
    checks: int = 0
    due: float = 0.0


@dataclass
class _DirWait:
    task_id: str
    dirpath: str
    folder_type: Literal["source", "output"]
    dues: List[float] = field(default_factory=list)


class EventInbox:
    """
    事件模式收件箱：observer 只入队，工作线程等 size+mtime 稳定后再回调。
    新目录会立刻扫一遍，并在 15s / 60s 后再补扫，避免子目录 watch 尚未挂上时漏文件。
    """

    def __init__(self, callback: Callable):
        self._callback = callback
        self._files: Dict[Tuple[str, str], _FileWait] = {}
        self._dirs: List[_DirWait] = []
        self._lock = Lock()
        self._stop = Event()
        self._thread: Optional[Thread] = None
        self._running = False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop.clear()
        self._thread = Thread(target=self._loop, name="MonitorInbox", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        with self._lock:
            self._files.clear()
            self._dirs.clear()

    def cancel(self, filepath: str, task_id: Optional[str] = None) -> None:
        with self._lock:
            if task_id is not None:
                self._files.pop((str(task_id), filepath), None)
                return
            for key in [k for k in self._files if k[1] == filepath]:
                self._files.pop(key, None)

    def submit_file(self, task_id: str, filepath: str, folder_type: Literal["source", "output"]) -> None:
        if not is_video_file(filepath) or is_incomplete_download(filepath):
            return
        stat = _safe_stat(filepath)
        if stat is None:
            return
        size, mtime = stat
        key = (str(task_id), filepath)
        now = time.monotonic()
        with self._lock:
            pending = self._files.get(key)
            if pending:
                if pending.size != size or pending.mtime != mtime:
                    pending.size = size
                    pending.mtime = mtime
                    pending.checks = 0
                    pending.due = now + _STABLE_DELAY
                return
            self._files[key] = _FileWait(
                task_id=task_id,
                filepath=filepath,
                folder_type=folder_type,
                size=size,
                mtime=mtime,
                due=now + _STABLE_DELAY,
            )

    def submit_directory(self, task_id: str, dirpath: str, folder_type: Literal["source", "output"]) -> None:
        self._scan_directory(task_id, dirpath, folder_type)
        now = time.monotonic()
        wait = _DirWait(
            task_id=task_id,
            dirpath=dirpath,
            folder_type=folder_type,
            dues=[now + delay for delay in _DIR_RESCAN_DELAYS],
        )
        with self._lock:
            if any(item.task_id == task_id and item.dirpath == dirpath for item in self._dirs):
                return
            self._dirs.append(wait)

    def _scan_directory(self, task_id: str, dirpath: str, folder_type: Literal["source", "output"]) -> None:
        if not os.path.isdir(dirpath):
            return
        files = [
            path for path in findAllFilesWithSuffix(dirpath, video_type, [], [])
            if not is_incomplete_download(path)
        ]
        if files:
            logger.info(f"Directory scan {dirpath}: {len(files)} video file(s)")
        for filepath in files:
            self.submit_file(task_id, filepath, folder_type)

    def _loop(self) -> None:
        while self._running and not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Monitor inbox tick failed")
            self._stop.wait(timeout=_TICK)

    def _tick(self) -> None:
        now = time.monotonic()
        ready_files: List[_FileWait] = []
        due_dirs: List[_DirWait] = []

        with self._lock:
            for key, item in list(self._files.items()):
                if item.due > now:
                    continue
                self._files.pop(key, None)
                ready_files.append(item)
            still_dirs = []
            for item in self._dirs:
                if item.dues and item.dues[0] <= now:
                    item.dues.pop(0)
                    due_dirs.append(item)
                if item.dues:
                    still_dirs.append(item)
            self._dirs = still_dirs

        for item in due_dirs:
            self._scan_directory(item.task_id, item.dirpath, item.folder_type)

        for item in ready_files:
            self._finish_file(item, now)

    def _finish_file(self, item: _FileWait, now: float) -> None:
        stat = _safe_stat(item.filepath)
        if stat is None:
            return
        size, mtime = stat
        if size != item.size or mtime != item.mtime:
            item.size = size
            item.mtime = mtime
            item.checks = 0
            item.due = now + _STABLE_DELAY
            with self._lock:
                self._files[(str(item.task_id), item.filepath)] = item
            return
        item.checks += 1
        if item.checks < _STABLE_CHECKS:
            item.due = now + _STABLE_DELAY
            with self._lock:
                self._files[(str(item.task_id), item.filepath)] = item
            return
        event = MonitorEvent(event_type="created", src_path=item.filepath)
        try:
            self._callback(event, item.task_id, item.filepath, item.folder_type)
        except Exception:
            logger.exception("Monitor inbox callback failed: %s", item.filepath)


def _safe_stat(filepath: str) -> Optional[Tuple[int, float]]:
    try:
        if not os.path.isfile(filepath):
            return None
        info = os.stat(filepath)
        return info.st_size, info.st_mtime
    except OSError:
        return None
