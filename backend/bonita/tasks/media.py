import logging

from celery import shared_task

from bonita.db import SessionFactory
from bonita.modules.media_service.factory import ensure_media_client
from bonita.services.celery_service import TASK_COLLECTION_SYNC, TASK_WATCH_HISTORY_SYNC
from bonita.services.setting_service import SettingService
from bonita.services.watch_sync_service import WatchSyncService
from bonita.tasks.decorators import manage_celery_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='emby:scan')
def celery_emby_scan(self, task_json, paths=None):
    logger.info("## [Emby扫描] START")
    try:
        client = ensure_media_client()
        if not client:
            logger.warning("## [Emby扫描] ⊘ 服务未初始化")
            return
        if paths:
            try:
                if client.refresh_libraries_for_paths(paths):
                    logger.info("## [Emby扫描] END")
                    return
            except Exception as e:
                logger.warning(f"## [Emby扫描] 按库刷新失败，改为全库刷新: {e}")
            else:
                logger.info("## [Emby扫描] 未能按库刷新，改为全库刷新")
        client.trigger_library_scan()
        logger.info("## [Emby扫描] END")
    except Exception as e:
        logger.error(f"## [Emby扫描] ✗ 失败: {str(e)}")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='watch_history:sync')
@manage_celery_task(TASK_WATCH_HISTORY_SYNC)
def celery_sync_watch_history(self, sources=None, days=30, limit=100, direction="from_server", force=False):
    logger.info(f"## [观看历史同步] START - 来源:{sources} direction={direction} force={force}")
    session = SessionFactory()
    requested_sources = sources
    if not requested_sources:
        requested_sources = ["emby"]
    elif isinstance(requested_sources, str):
        requested_sources = [requested_sources]
    else:
        requested_sources = list(requested_sources)

    synced_sources = []
    try:
        setting_service = SettingService(session)

        if "emby" in requested_sources:
            emby_settings = setting_service.get_emby_settings()
            if emby_settings.get("enabled"):
                client = ensure_media_client("emby")
                if client:
                    WatchSyncService(session).sync_history(direction=direction, force=force)
                    synced_sources.append("emby")
                    logger.info("  ✓ Emby 同步完成")
                else:
                    logger.warning("  ⊘ Emby 服务未初始化")
            else:
                logger.info("  ⊘ Emby 同步已禁用")

        unsupported_sources = set(requested_sources) - {"emby"}
        for source in unsupported_sources:
            logger.info(f"  ⊘ {source} 暂未支持")

        logger.info(f"## [观看历史同步] END - 已同步:{synced_sources}")
        return {
            "requested_sources": requested_sources,
            "synced_sources": synced_sources,
            "days": days,
            "limit": limit,
            "direction": direction,
            "force": force,
        }
    finally:
        session.close()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='collection:sync')
@manage_celery_task(TASK_COLLECTION_SYNC)
def celery_sync_collection(self, collection_id=None, direction="from_server"):
    logger.info(f"## [合集同步] START - collection_id={collection_id} direction={direction}")
    session = SessionFactory()
    try:
        from bonita.services.collection_service import CollectionService

        service = CollectionService(session)
        if collection_id is not None:
            collection = service.get_by_id(collection_id)
            if not collection:
                raise RuntimeError(f"合集不存在: {collection_id}")
            service.sync_one(collection, direction=direction)
            synced = 1
        else:
            synced = service.sync_all(direction=direction)
        logger.info(f"## [合集同步] END - synced={synced}")
        return {
            "collection_id": collection_id,
            "direction": direction,
            "synced": synced,
        }
    finally:
        session.close()
