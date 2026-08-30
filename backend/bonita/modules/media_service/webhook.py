import logging

from bonita.modules.media_service.client import (
    ITEM_EPISODE,
    ITEM_MOVIE,
    ITEM_SEASON,
    ITEM_SERIES,
    ITEM_VIDEO,
    SOURCE_EMBY,
    WEBHOOK_FAVORITE,
    WEBHOOK_IGNORED,
    WEBHOOK_LIBRARY_NEW,
    WEBHOOK_TEST,
    WEBHOOK_UNPLAYED,
    WEBHOOK_WATCH,
    RemoteItem,
    source_label,
)
from bonita.modules.media_service.factory import ensure_media_client
from bonita.modules.media_service.watch import apply_remote_watch

logger = logging.getLogger(__name__)

_SYNCABLE_ITEM_TYPES = {ITEM_MOVIE, ITEM_VIDEO, ITEM_EPISODE, ITEM_SERIES, ITEM_SEASON}


def is_syncable_item(item: RemoteItem) -> bool:
    if item.item_type in (ITEM_SERIES, ITEM_SEASON):
        return True
    if item.is_folder:
        return False
    return item.item_type in _SYNCABLE_ITEM_TYPES or not item.item_type


def handle_webhook_event(session, payload: dict, source=SOURCE_EMBY) -> str:
    client = ensure_media_client(source)
    if not client:
        logger.warning(f"  ⊘ {source_label(source)}服务未初始化")
        return "ignored"

    event = client.parse_webhook(payload)
    if event.kind == WEBHOOK_IGNORED:
        return "ignored"
    if event.kind == WEBHOOK_TEST:
        logger.info(f"  ✓ 收到 {source_label(source)} Webhook 测试事件")
        return "test"

    if (
        event.kind in (WEBHOOK_WATCH, WEBHOOK_UNPLAYED, WEBHOOK_FAVORITE)
        and client.configured_user
        and event.user_name
        and event.user_name.lower() != client.configured_user.lower()
    ):
        logger.info(f"  ⊘ 忽略其他用户的 Webhook: {event.user_name}")
        return "skipped"

    if not event.items:
        logger.warning("  ⊘ Webhook 缺少 Item")
        return "ignored"

    synced = 0
    for item in event.items:
        if not is_syncable_item(item):
            continue
        if event.kind == WEBHOOK_LIBRARY_NEW:
            apply_remote_watch(session, client, item, force=False)
            logger.info(f"  ✓ Webhook 新媒体入库: {item.title}")
        elif event.kind == WEBHOOK_FAVORITE:
            apply_remote_watch(session, client, item, force=True)
            favorite = bool(item.watch and item.watch.favorite)
            logger.info(f"  ✓ Webhook 同步收藏: {item.title} favorite={favorite}")
        elif event.kind == WEBHOOK_UNPLAYED:
            apply_remote_watch(session, client, item, force=True)
            logger.info(f"  ✓ Webhook 标记未观看: {item.title}")
        else:
            apply_remote_watch(session, client, item, force=False)
            logger.info(f"  ✓ Webhook 同步观看状态: {event.raw_event} {item.title}")
        synced += 1
    return "synced" if synced else "ignored"
