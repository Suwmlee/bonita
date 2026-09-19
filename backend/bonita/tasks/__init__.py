"""Celery 任务定义。worker 通过 import bonita.tasks 注册全部任务。"""

from bonita.tasks.media import (
    celery_emby_scan,
    celery_sync_collection,
    celery_sync_watch_history,
)
from bonita.tasks.scraping import (
    celery_import_nfo,
    celery_reload_scrapinglib,
    celery_scrapping,
)
from bonita.tasks.transfer import (
    celery_clean_others,
    celery_transfer_entry,
    celery_transfer_group,
)

__all__ = [
    "celery_clean_others",
    "celery_emby_scan",
    "celery_import_nfo",
    "celery_reload_scrapinglib",
    "celery_scrapping",
    "celery_sync_collection",
    "celery_sync_watch_history",
    "celery_transfer_entry",
    "celery_transfer_group",
]
