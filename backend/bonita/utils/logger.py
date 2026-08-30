import logging
import os
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

from bonita.core.config import settings

task_id_ctx = ContextVar("task_id", default="")

LOG_BACKUP_COUNT = 5


class ContextFilter(logging.Filter):
    """
    日志上下文过滤器，添加额外的上下文信息到日志记录中
    """

    def filter(self, record: logging.LogRecord):
        # 这里可以添加任何你想要的上下文信息，例如请求ID、用户ID等
        record.task_id = task_id_ctx.get()
        return True


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


def list_log_files(log_file_path: str | None = None) -> list[str]:
    """当前日志 + 轮转备份，按从旧到新排序：bonita.5.log … bonita.1.log、bonita.log。"""
    path = os.path.abspath(log_file_path or settings.LOGGING_LOCATION)
    directory, filename = os.path.split(path)
    stem, ext = os.path.splitext(filename)
    found: list[str] = []
    for i in range(LOG_BACKUP_COUNT, 0, -1):
        backup = os.path.join(directory, f"{stem}.{i}{ext}")
        if os.path.isfile(backup):
            found.append(backup)
    if os.path.isfile(path):
        found.append(path)
    return found


def init_log_config():
    """
    日志配置
    """
    max_log_size = 10 * 1024 * 1024  # 10 MB
    backup_count = LOG_BACKUP_COUNT
    formatter = logging.Formatter(settings.LOGGING_FORMAT)
    file_handler = RotatingFileHandler(
        settings.LOGGING_LOCATION,
        maxBytes=max_log_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.namer = _log_rotation_namer
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ContextFilter())

    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        handlers=[file_handler],
        force=True,
    )
