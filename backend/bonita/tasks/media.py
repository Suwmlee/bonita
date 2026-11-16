import logging

from celery import shared_task

from bonita.db import SessionFactory
from bonita.modules.media_service.factory import ensure_media_client
from bonita.modules.media_service.client import SOURCE_EMBY, source_label
from bonita.services.celery_service import (
    TASK_ACTOR_EMBY_PHOTO_SYNC,
    TASK_COLLECTION_SYNC,
    TASK_MEDIA_LIBRARY_SCAN,
    TASK_PLAYLIST_SYNC,
    TASK_WATCH_HISTORY_SYNC,
    TaskProgressTracker,
)
from bonita.services.setting_service import SettingService
from bonita.services.watch_sync_service import WatchSyncService
from bonita.tasks.decorators import manage_celery_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name="media:library_scan")
@manage_celery_task(TASK_MEDIA_LIBRARY_SCAN)
def celery_media_library_scan(self, task_json=None, paths=None, source=SOURCE_EMBY):
    label = source_label(source)
    logger.info(f"## [{label}扫描] START source={source}")
    client = ensure_media_client(source)
    if not client:
        raise RuntimeError(f"{label}服务未初始化")
    if paths and hasattr(client, "refresh_libraries_for_paths"):
        try:
            if client.refresh_libraries_for_paths(paths):
                logger.info(f"## [{label}扫描] END")
                return {"paths": list(paths), "mode": "by_path", "source": source}
        except Exception as e:
            logger.warning(f"## [{label}扫描] 按库刷新失败，改为全库刷新: {e}")
        else:
            logger.info(f"## [{label}扫描] 未能按库刷新，改为全库刷新")
    client.trigger_library_scan()
    logger.info(f"## [{label}扫描] END")
    return {"paths": list(paths) if paths else None, "mode": "full", "source": source}


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
    supported = {"emby", "plex"}
    try:
        setting_service = SettingService(session)

        if "emby" in requested_sources:
            emby_settings = setting_service.get_emby_settings()
            if emby_settings.get("enabled"):
                client = ensure_media_client("emby")
                if client:
                    WatchSyncService(session).sync_history(
                        direction=direction, force=force, source="emby"
                    )
                    synced_sources.append("emby")
                    logger.info("  ✓ Emby 同步完成")
                else:
                    logger.warning("  ⊘ Emby 服务未初始化")
            else:
                logger.info("  ⊘ Emby 同步已禁用")

        if "plex" in requested_sources:
            plex_settings = setting_service.get_plex_settings()
            if plex_settings.get("enabled"):
                client = ensure_media_client("plex")
                if client:
                    WatchSyncService(session).sync_history(
                        direction=direction, force=force, source="plex"
                    )
                    synced_sources.append("plex")
                    logger.info("  ✓ Plex 同步完成")
                else:
                    logger.warning("  ⊘ Plex 服务未初始化")
            else:
                logger.info("  ⊘ Plex 同步已禁用")

        unsupported_sources = set(requested_sources) - supported
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


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    dont_autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="actor_emby_photo:sync",
)
@manage_celery_task(TASK_ACTOR_EMBY_PHOTO_SYNC)
def celery_sync_actor_emby_photos(self, force: bool = False):
    logger.info(f"## [演员头像同步Emby] START force={force}")
    session = SessionFactory()
    try:
        from bonita.services.actor_emby_sync_service import ActorEmbySyncService

        tracker = TaskProgressTracker(self.request.id, total_steps=100)
        tracker.set_progress(1.0, "准备同步演员头像")

        def on_progress(pct: float, step: str):
            tracker.set_progress(pct, step)

        result = ActorEmbySyncService(session).sync_photos(
            force=bool(force),
            progress=on_progress,
        )
        logger.info(f"## [演员头像同步Emby] END {result}")
        return result
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


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='playlist:sync')
@manage_celery_task(TASK_PLAYLIST_SYNC)
def celery_sync_playlist(self, playlist_id=None, direction="from_server"):
    logger.info(f"## [播放列表同步] START - playlist_id={playlist_id} direction={direction}")
    session = SessionFactory()
    try:
        from bonita.services.playlist_service import PlaylistService

        service = PlaylistService(session)
        if playlist_id is not None:
            playlist = service.get_by_id(playlist_id)
            if not playlist:
                raise RuntimeError(f"播放列表不存在: {playlist_id}")
            service.sync_one(playlist, direction=direction)
            synced = 1
        else:
            synced = service.sync_all(direction=direction)
        logger.info(f"## [播放列表同步] END - synced={synced}")
        return {
            "playlist_id": playlist_id,
            "direction": direction,
            "synced": synced,
        }
    finally:
        session.close()
