import logging
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

from bonita.core.config import settings

task_id_ctx = ContextVar("task_id", default="")


class ContextFilter(logging.Filter):
    """
    日志上下文过滤器，添加额外的上下文信息到日志记录中
    """

    def filter(self, record: logging.LogRecord):
        # 这里可以添加任何你想要的上下文信息，例如请求ID、用户ID等
        record.task_id = task_id_ctx.get()
        return True


def init_log_config():
    """
    日志配置
    """
    max_log_size = 5 * 1024 * 1024  # 5 MB
    backup_count = 5
    formatter = logging.Formatter(settings.LOGGING_FORMAT)
    file_handler = RotatingFileHandler(
        settings.LOGGING_LOCATION,
        maxBytes=max_log_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ContextFilter())

    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        handlers=[file_handler],
        force=True,
    )
