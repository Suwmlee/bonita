import logging

from bonita.db.models.watch_history import WatchHistory
from bonita.modules.media_service.client import (
    ITEM_SEASON,
    SOURCE_EMBY,
    MediaServerClient,
    RemoteItem,
    is_to_server,
    source_label,
)
from bonita.modules.media_service.factory import ensure_media_client
from bonita.modules.media_service.matching import (
    ensure_series,
    find_transfer_record,
    resolve_media_item,
)

logger = logging.getLogger(__name__)


def sync_watch_history(session, direction="from_server", force=False, source=SOURCE_EMBY):
    """同步媒体服务器和 Bonita 之间的观看记录。"""
    label = source_label(source)
    try:
        client = ensure_media_client(source)
        if not client:
            logger.warning(f"  ⊘ {label}服务未初始化")
            return

        logger.info(f"  → 获取{label}媒体项目...")
        items = client.list_user_items()
        if not items:
            logger.info(f"  ⊘ {label} 中没有媒体项目")
            return

        total_movies = sum(1 for item in items if item.item_type == "movie")
        total_series = sum(1 for item in items if item.item_type == "series")
        total_seasons = sum(1 for item in items if item.item_type == "season")
        total_episodes = sum(1 for item in items if item.item_type == "episode")
        logger.info(
            f"  找到 {total_movies} 个电影, {total_series} 部剧, "
            f"{total_seasons} 季, {total_episodes} 集"
        )

        processed = 0
        synced = 0
        to_server = is_to_server(direction)
        for item in items:
            try:
                processed += 1
                if to_server:
                    if sync_item_to_server(session, client, item, force):
                        synced += 1
                else:
                    apply_remote_watch(session, client, item, force)
                    synced += 1
            except Exception as e:
                logger.error(f"  ✗ 处理项目失败: {e}")
                continue

        logger.info(f"  ✓ 同步完成 - 处理:{processed} 同步:{synced}")
        return

    except Exception as e:
        logger.error(f"  ✗ {label}同步失败: {e}")
        raise


def apply_remote_watch(session, client: MediaServerClient, item: RemoteItem, force=False):
    """将单个远端条目同步为本地 MediaItem + WatchHistory。"""
    if not item or not item.remote_id:
        return None

    if item.item_type == ITEM_SEASON:
        _propagate_season_favorite(session, client, item, force)
        return None

    media_item = resolve_media_item(session, item, client, create=True)
    if not media_item:
        return None

    title = media_item.title
    watch = item.watch
    duration = watch.duration_seconds if watch else 0
    watched = bool(watch.played) if watch else False
    is_favorite = bool(watch.favorite) if watch else False
    if media_item.media_type == "episode" and media_item.series_id:
        parent_history = session.query(WatchHistory).filter(
            WatchHistory.media_item_id == media_item.series_id
        ).first()
        if parent_history and parent_history.favorite:
            is_favorite = True
    watch_count = watch.play_count if watch else 1
    play_progress = watch.play_progress if watch else (100.0 if watched else 0.0)

    existing_record = session.query(WatchHistory).filter(
        WatchHistory.media_item_id == media_item.id
    ).first()
    if existing_record:
        final_watched = watched if force else (existing_record.watched or watched)
        final_favorite = is_favorite if force else (existing_record.favorite or is_favorite)
        has_record_changes = (
            existing_record.watched != final_watched
            or existing_record.watch_count != watch_count
            or existing_record.favorite != final_favorite
            or existing_record.play_progress != play_progress
            or existing_record.duration != duration
        )
        if has_record_changes:
            existing_record.watched = final_watched
            existing_record.watch_count = watch_count
            existing_record.favorite = final_favorite
            existing_record.play_progress = play_progress
            existing_record.duration = duration
            session.commit()
            logger.info(f"    ✓ 更新观看记录: {title}")
    else:
        new_record = WatchHistory(
            media_item_id=media_item.id,
            watched=watched,
            watch_count=watch_count,
            favorite=is_favorite,
            play_progress=play_progress,
            duration=duration,
        )
        new_record.create(session)
        logger.info(f"    ✓ 创建观看记录: {title}")

    if media_item.media_type == "tvshow" and is_favorite:
        propagate_favorite_to_episodes(session, media_item.id)


def sync_item_to_server(session, client: MediaServerClient, item: RemoteItem, force=False):
    media_item = resolve_media_item(session, item, client, create=False)
    if not media_item:
        return False

    watch_history = session.query(WatchHistory).filter(
        WatchHistory.media_item_id == media_item.id
    ).first()
    if not watch_history:
        return False

    remote_watch = item.watch
    remote_watched = bool(remote_watch.played) if remote_watch else False
    remote_favorite = bool(remote_watch.favorite) if remote_watch else False
    label = media_item.number or media_item.title

    updated = False
    if watch_history.watched and not remote_watched:
        client.mark_as_played(item.remote_id)
        logger.info(f"    ✓ 标记为已观看: {label}")
        updated = True
    elif not watch_history.watched and remote_watched and force:
        client.mark_as_unplayed(item.remote_id)
        logger.info(f"    ✓ 标记为未观看: {label}")
        updated = True

    if watch_history.favorite and not remote_favorite:
        client.mark_as_favorite(item.remote_id)
        logger.info(f"    ♥ 标记为喜爱: {label}")
        updated = True
    elif not watch_history.favorite and remote_favorite and force:
        client.unmark_as_favorite(item.remote_id)
        logger.info(f"    ✓ 取消喜爱: {label}")
        updated = True

    return updated


def _propagate_season_favorite(session, client: MediaServerClient, item: RemoteItem, force=False):
    is_favorite = bool(item.watch and item.watch.favorite)
    if not is_favorite and not force:
        return
    record, _extra = find_transfer_record(session, item.path)
    series = ensure_series(session, item, record, client, create=True)
    if not series:
        return
    season = item.season
    if season < 0:
        return
    if is_favorite:
        propagate_favorite_to_episodes(session, series.id, season)
        logger.info(f"    ♥ 季收藏已同步到各集: {series.title} S{season:02d}")


def propagate_favorite_to_episodes(session, series_id, season=None):
    from bonita.db.models.mediaitem import MediaItem

    query = session.query(MediaItem).filter(
        MediaItem.media_type == "episode",
        MediaItem.series_id == series_id,
    )
    if season is not None and season >= 0:
        query = query.filter(MediaItem.season_number == season)
    updated = 0
    for episode in query.all():
        history = session.query(WatchHistory).filter(
            WatchHistory.media_item_id == episode.id
        ).first()
        if history:
            if not history.favorite:
                history.favorite = True
                updated += 1
        else:
            WatchHistory(
                media_item_id=episode.id,
                watched=False,
                watch_count=0,
                favorite=True,
            ).create(session)
            updated += 1
    if updated:
        session.commit()
        logger.info(f"    ♥ 已将收藏同步到 {updated} 集")
