import fcntl
import logging
import os
import re
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

from bonita.core.config import settings

task_id_ctx = ContextVar("task_id", default="")

LOG_BACKUP_COUNT = 5
_MAX_LOG_BYTES = 10 * 1024 * 1024

# 这些库在 DEBUG 下会把 HTTP 报文、调度心跳、与业务重复的任务轨迹打进同一份日志。
# floor 是允许的最详细级别：应用开到 DEBUG 时它们也不会低于这个级别。
_LIBRARY_LEVEL_FLOOR = {
    "urllib3": logging.WARNING,
    "requests": logging.WARNING,
    "PIL": logging.WARNING,
    "qbittorrentapi": logging.INFO,
    # beat 的 “Sending due task” 与 after_task_publish 的 TASK_SENT 重复
    "celery.beat": logging.WARNING,
    "celery.app.trace": logging.WARNING,
    "celery.worker.strategy": logging.WARNING,
    "celery.pool": logging.WARNING,
    "kombu": logging.WARNING,
    "amqp": logging.WARNING,
}

_NEW_LINE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\] (?P<level>\w+) (?P<module>[\w.]+)"
    r"(?: \[(?P<task>[^\]]+)\])?: (?P<message>.*)$"
)
_OLD_LINE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\] (?P<level>\w+) in (?P<module>[\w.]+): (?P<message>.*)$"
)
_OLD_META = re.compile(
    r"^PID:\d+ TID:\d+ (?:\[(?P<task>[^\]]*)\] )?(?P<message>.*)$"
)


class _Formatter(logging.Formatter):
    """有任务 ID 才写入行内，避免每一行都带上空的 []。"""

    def format(self, record: logging.LogRecord) -> str:
        task_id = task_id_ctx.get()
        record.task_id = task_id
        record.task_suffix = f" [{task_id}]" if task_id else ""
        return super().format(record)


def _log_rotation_namer(default_name: str) -> str:
    """把 RotatingFileHandler 默认的 bonita.log.1 改成 bonita.1.log。"""
    directory, filename = os.path.split(default_name)
    if filename.endswith(".log"):
        return default_name
    stem, separator, suffix = filename.rpartition(".")
    if separator and stem.endswith(".log") and suffix.isdigit():
        name = stem[: -len(".log")]
        return os.path.join(directory, f"{name}.{suffix}.log")
    return default_name


class SharedRotatingFileHandler(RotatingFileHandler):
    """多进程可同时写入的按大小轮转 handler。

    标准库 RotatingFileHandler 只看自己打开的文件描述符。某个进程 rename
    之后，其余进程仍往旧 inode 写，于是较新的日志会留在 bonita.1.log 这类备份里。
    这里用独立锁文件串行化写入和轮转，并在路径 inode 变化时重新按路径打开。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock_path = self.baseFilename + ".lock"
        self._lock_fp = None
        self._inode: int | None = None
        self._remember_inode()

    def _remember_inode(self) -> None:
        if self.stream is None:
            self._inode = None
            return
        try:
            self._inode = os.fstat(self.stream.fileno()).st_ino
        except OSError:
            self._inode = None

    def _ensure_stream(self) -> None:
        try:
            inode = os.stat(self.baseFilename).st_ino
        except OSError:
            inode = None
        if self.stream is not None and inode is not None and inode == self._inode:
            return
        if self.stream is not None:
            self.stream.close()
            self.stream = None
        self.stream = self._open()
        self._remember_inode()

    def _acquire(self) -> None:
        self._lock_fp = open(self._lock_path, "a")
        fcntl.flock(self._lock_fp.fileno(), fcntl.LOCK_EX)

    def _release(self) -> None:
        lock_fp = self._lock_fp
        self._lock_fp = None
        if lock_fp is None:
            return
        try:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fp.close()

    def shouldRollover(self, record: logging.LogRecord) -> bool:
        if self.maxBytes <= 0:
            return False
        if self.stream is None:
            self.stream = self._open()
            self._remember_inode()
        self.stream.seek(0, os.SEEK_END)
        message = f"{self.format(record)}{self.terminator}"
        encoded = len(message.encode("utf-8", errors="replace"))
        return self.stream.tell() + encoded >= self.maxBytes

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._acquire()
            try:
                self._ensure_stream()
                if self.shouldRollover(record):
                    self.doRollover()
                    self._remember_inode()
                logging.FileHandler.emit(self, record)
                if self.stream is not None:
                    self.stream.flush()
            finally:
                self._release()
        except Exception:
            self.handleError(record)


def backup_log_path(log_file_path: str, index: int) -> str:
    path = os.path.abspath(log_file_path)
    directory, filename = os.path.split(path)
    stem, ext = os.path.splitext(filename)
    return os.path.join(directory, f"{stem}.{index}{ext}")


def list_log_files(log_file_path: str | None = None) -> list[str]:
    """当前日志 + 轮转备份，按从旧到新排序：bonita.5.log … bonita.1.log、bonita.log。"""
    path = os.path.abspath(log_file_path or settings.LOGGING_LOCATION)
    found: list[str] = []
    for index in range(LOG_BACKUP_COUNT, 0, -1):
        backup = backup_log_path(path, index)
        if os.path.isfile(backup):
            found.append(backup)
    if os.path.isfile(path):
        found.append(path)
    return found


def parse_log_line(line: str) -> dict | None:
    """解析一行日志。兼容旧格式里的 PID/TID，展示时去掉这些重复字段。"""
    stripped = line.strip()
    if not stripped:
        return None
    matched = _NEW_LINE.match(stripped)
    task_id = ""
    if matched:
        task_id = matched.group("task") or ""
        message = matched.group("message")
    else:
        matched = _OLD_LINE.match(stripped)
        if not matched:
            return None
        message = matched.group("message")
        meta = _OLD_META.match(message)
        if meta:
            task_id = meta.group("task") or ""
            message = meta.group("message")
    if task_id and task_id not in message:
        message = f"[{task_id}] {message}"
    return {
        "timestamp": matched.group("timestamp"),
        "level": matched.group("level"),
        "module": matched.group("module"),
        "message": message,
    }


def parse_log_text(text: str) -> list[dict]:
    """把一段日志文本解析成条目，异常栈等续行并进上一条。"""
    entries: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        parsed = parse_log_line(line)
        if parsed:
            current = parsed
            entries.append(current)
        elif current is not None and line.strip():
            current["message"] += "\n" + line
    return entries


def _normalize_level(level: str | None) -> str | None:
    if not level:
        return None
    value = level.strip().lower()
    if value == "warn":
        value = "warning"
    if value not in {"debug", "info", "warning", "error", "critical"}:
        return None
    return value


def _read_tail_text(path: str, size: int, window: int) -> str:
    start = 0 if window >= size else size - window
    with open(path, "rb") as handle:
        handle.seek(start)
        data = handle.read()
    if start > 0:
        newline = data.find(b"\n")
        if newline < 0:
            return ""
        data = data[newline + 1 :]
    return data.decode("utf-8", errors="replace")


def _tail_entries(path: str, limit: int, level: str | None) -> list[dict]:
    """单个文件里最新的 limit 条。文件之间时间重叠时，合并方再按时间截取。"""
    try:
        size = os.path.getsize(path)
    except OSError:
        return []
    if size <= 0 or limit <= 0:
        return []

    window = 128 * 1024
    while True:
        try:
            text = _read_tail_text(path, size, window)
        except OSError:
            return []
        entries = parse_log_text(text)
        if level:
            entries = [entry for entry in entries if entry["level"].lower() == level]
        if len(entries) >= limit or window >= size:
            return entries[-limit:]
        window = min(size, window * 4)


def read_recent_logs(
    log_file_path: str | None = None,
    limit: int = 1000,
    level: str | None = None,
) -> list[dict]:
    """从当前日志和轮转备份中取最近 limit 条，按时间排序。

    备份编号默认代表从旧到新，但多进程轮转曾经把更新的内容留在编号更大的文件里。
    每个文件各取最近 limit 条再按时间合并，得到的才是真正最新的一段。
    """
    if limit <= 0:
        return []
    level_norm = _normalize_level(level)
    files = list_log_files(log_file_path)
    ranked: list[tuple[str, int, int, dict]] = []
    for file_index, path in enumerate(files):
        for seq, entry in enumerate(_tail_entries(path, limit, level_norm)):
            ranked.append((entry["timestamp"], file_index, seq, entry))
    ranked.sort()
    return [item[3] for item in ranked[-limit:]]


class LogFollower:
    """从当前日志文件末尾接着读。轮转后先补完旧 inode 上还没读到的部分。"""

    def __init__(self, log_file_path: str | None = None):
        self.path = os.path.abspath(log_file_path or settings.LOGGING_LOCATION)
        self.offset = 0
        self.inode: int | None = None
        self.pending = b""

    def prime(self) -> None:
        """从当前末尾开始，避免把已有内容再推一遍。"""
        self.pending = b""
        if not os.path.exists(self.path):
            self.inode = None
            self.offset = 0
            return
        stat = os.stat(self.path)
        self.inode = stat.st_ino
        self.offset = stat.st_size

    def read_new(self) -> list[dict]:
        if not os.path.exists(self.path):
            self.inode = None
            self.offset = 0
            self.pending = b""
            return []

        stat = os.stat(self.path)
        if self.inode is None:
            self.inode = stat.st_ino
            self.offset = 0
        elif stat.st_ino != self.inode:
            drained = self._drain_rotated()
            self.inode = stat.st_ino
            self.offset = 0
            return drained + self._read_available()

        if stat.st_size < self.offset:
            self.offset = 0
            self.pending = b""
        return self._read_available()

    def _drain_rotated(self) -> list[dict]:
        """当前路径已被 rename 时，按 inode 把还没读到的备份补齐。

        两次轮询之间可能连转多档，旧 inode 不一定还在 bonita.1.log。
        找到它之后，再按从旧到新读完编号更小的备份。
        """
        old_inode = self.inode
        pending = self.pending
        self.pending = b""
        if old_inode is None:
            return []

        found_index: int | None = None
        for index in range(1, LOG_BACKUP_COUNT + 1):
            try:
                stat = os.stat(backup_log_path(self.path, index))
            except OSError:
                continue
            if stat.st_ino == old_inode:
                found_index = index
                break
        if found_index is None:
            return []

        entries = self._read_slice(
            backup_log_path(self.path, found_index), self.offset, pending
        )
        for index in range(found_index - 1, 0, -1):
            path = backup_log_path(self.path, index)
            if os.path.isfile(path):
                entries.extend(self._read_slice(path, 0, b""))
        return entries

    def _read_slice(self, path: str, offset: int, prefix: bytes) -> list[dict]:
        try:
            with open(path, "rb") as handle:
                handle.seek(offset)
                data = prefix + handle.read()
        except OSError:
            return []
        if not data:
            return []
        return parse_log_text(data.decode("utf-8", errors="replace"))

    def _read_available(self) -> list[dict]:
        with open(self.path, "rb") as handle:
            handle.seek(self.offset)
            chunk = handle.read()
            self.offset = handle.tell()
        return self._consume(chunk)

    def _consume(self, chunk: bytes) -> list[dict]:
        data = self.pending + chunk
        if not data:
            return []
        if data.endswith(b"\n"):
            complete, self.pending = data, b""
        else:
            newline = data.rfind(b"\n")
            if newline < 0:
                self.pending = data
                return []
            complete, self.pending = data[: newline + 1], data[newline + 1 :]
        return parse_log_text(complete.decode("utf-8", errors="replace"))


def cap_library_logs() -> None:
    """压住第三方库的详细日志，避免把业务日志淹没。"""
    app_level = settings.LOGGING_LEVEL
    if not isinstance(app_level, int):
        resolved = logging.getLevelName(str(app_level).upper())
        app_level = resolved if isinstance(resolved, int) else logging.INFO
    for name, floor in _LIBRARY_LEVEL_FLOOR.items():
        logging.getLogger(name).setLevel(max(floor, app_level))


def init_log_config():
    """日志配置。API 进程和 Celery 进程都会调用，写入同一份可轮转的文件。"""
    root = logging.getLogger()
    if any(isinstance(handler, SharedRotatingFileHandler) for handler in root.handlers):
        root.setLevel(settings.LOGGING_LEVEL)
        cap_library_logs()
        return

    directory = os.path.dirname(os.path.abspath(settings.LOGGING_LOCATION))
    if directory:
        os.makedirs(directory, exist_ok=True)

    formatter = _Formatter(settings.LOGGING_FORMAT)
    file_handler = SharedRotatingFileHandler(
        settings.LOGGING_LOCATION,
        maxBytes=_MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.namer = _log_rotation_namer
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        handlers=[file_handler],
        force=True,
    )
    cap_library_logs()
