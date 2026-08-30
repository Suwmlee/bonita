import logging
from datetime import datetime

from bonita.db.models.collection import Collection, CollectionItem
from bonita.db.models.mediaitem import MediaItem
from bonita.modules.media_service.client import (
    ITEM_EPISODE,
    ITEM_MOVIE,
    ITEM_SERIES,
    ITEM_VIDEO,
    SOURCE_EMBY,
    is_to_server,
    source_label,
)
from bonita.modules.media_service.factory import require_media_client
from bonita.modules.media_service.matching import (
    find_remote_id_for_media_item,
    media_item_label,
    resolve_collection_member,
)

logger = logging.getLogger(__name__)

_COLLECTION_MEMBER_TYPES = {ITEM_MOVIE, ITEM_VIDEO, ITEM_EPISODE, ITEM_SERIES}


def collection_source(collection: Collection) -> str:
    return collection.source or SOURCE_EMBY


def add_and_sync_collection(
    session, external_id: str, name: str = None, source: str = SOURCE_EMBY
) -> Collection:
    client = require_media_client(source)
    collection = (
        session.query(Collection)
        .filter(Collection.source == source, Collection.external_id == external_id)
        .first()
    )
    if not collection:
        collection = Collection(
            source=source,
            external_id=external_id,
            name=(name or "").strip() or external_id,
        )
        collection.create(session)
    elif name and name.strip() and collection.name in ("", collection.external_id):
        collection.name = name.strip()
        session.commit()
    refresh_collection_meta(session, collection, fallback_name=name)
    return sync_collection_members(session, collection)


def refresh_collection_meta(session, collection: Collection, fallback_name: str = None):
    from bonita.modules.media_service.factory import get_media_client

    client = get_media_client(collection_source(collection))
    if not client:
        return
    details = client.get_user_item(collection.external_id) or client.get_item(collection.external_id)
    resolved_name = (
        (details.title if details else "").strip()
        or (fallback_name or "").strip()
        or collection.name
        or collection.external_id
    )
    image_tag = details.image_tag if details else None
    changed = False
    if resolved_name and collection.name != resolved_name:
        collection.name = resolved_name
        changed = True
    if image_tag and collection.image_tag != image_tag:
        collection.image_tag = image_tag
        changed = True
    if changed:
        session.commit()


def _refresh_member_counts(session, collection: Collection, remote_item_count=None, touch_sync=False):
    collection.matched_count = session.query(CollectionItem).filter(
        CollectionItem.collection_id == collection.id
    ).count()
    if remote_item_count is not None:
        collection.item_count = remote_item_count
    if touch_sync:
        collection.last_sync_at = datetime.now()
    session.commit()
    session.refresh(collection)


def sync_collection_members(session, collection: Collection, direction: str = "from_server") -> Collection:
    if is_to_server(direction):
        return sync_collection_to_server(session, collection)
    return sync_collection_from_server(session, collection)


def sync_collection_from_server(session, collection: Collection) -> Collection:
    source = collection_source(collection)
    client = require_media_client(source)
    label = source_label(source)
    logger.info(f"  → 合集 {collection.name}: 从 {label} 拉取成员")
    refresh_collection_meta(session, collection)
    boxset_items = client.get_collection_items(collection.external_id)
    existing = {
        row.media_item_id: row
        for row in session.query(CollectionItem).filter(
            CollectionItem.collection_id == collection.id
        ).all()
    }
    existing_remote_ids = {
        row.external_item_id for row in existing.values() if row.external_item_id
    }
    added = 0
    unmatched = 0
    for item in boxset_items:
        if item.item_type not in _COLLECTION_MEMBER_TYPES:
            continue
        remote_id = item.remote_id
        if remote_id and remote_id in existing_remote_ids:
            continue
        media_item = resolve_collection_member(session, item, client)
        if not media_item:
            unmatched += 1
            logger.info(
                f"    ⊘ 合集 {collection.name}: 未匹配 "
                f"{item.title or item.remote_id} path={item.path}"
            )
            continue
        row = existing.get(media_item.id)
        if row:
            if remote_id and row.external_item_id != remote_id:
                row.external_item_id = remote_id
                existing_remote_ids.add(remote_id)
            continue
        member = CollectionItem(
            collection_id=collection.id,
            media_item_id=media_item.id,
            external_item_id=remote_id,
        )
        session.add(member)
        existing[media_item.id] = member
        if remote_id:
            existing_remote_ids.add(remote_id)
        added += 1
    session.flush()
    _refresh_member_counts(
        session,
        collection,
        remote_item_count=len(boxset_items),
        touch_sync=True,
    )
    logger.info(
        f"    ✓ 合集 {collection.name}: 从 {label} 新增 {added} 项, "
        f"未匹配 {unmatched} 项, 本地 {collection.matched_count} 项, "
        f"{label} {collection.item_count} 项"
    )
    return collection


def sync_collection_to_server(session, collection: Collection) -> Collection:
    source = collection_source(collection)
    client = require_media_client(source)
    label = source_label(source)
    logger.info(f"  → 合集 {collection.name}: 开始回写 {label}")
    refresh_collection_meta(session, collection)
    boxset_items = client.get_collection_items(collection.external_id)
    remote_ids = {item.remote_id for item in boxset_items if item.remote_id}
    members = session.query(CollectionItem).filter(
        CollectionItem.collection_id == collection.id
    ).all()
    wanted_ids = set()
    unresolved = 0
    for member in members:
        media_item = session.query(MediaItem).filter(
            MediaItem.id == member.media_item_id
        ).first()
        resolved_id = member.external_item_id
        already_in_collection = resolved_id and resolved_id in remote_ids
        is_number = bool(media_item and (media_item.number or "").strip())
        if not already_in_collection:
            looked_up = None
            if media_item:
                looked_up = find_remote_id_for_media_item(session, client, media_item)
            if looked_up:
                if resolved_id and resolved_id != looked_up:
                    logger.info(
                        f"    ↻ 合集 {collection.name}: "
                        f"{media_item_label(media_item)} {label} Id "
                        f"{resolved_id} → {looked_up}"
                    )
                resolved_id = looked_up
                member.external_item_id = looked_up
            elif is_number:
                resolved_id = None
        if resolved_id:
            wanted_ids.add(resolved_id)
        else:
            unresolved += 1
            logger.warning(
                f"    ⊘ 合集 {collection.name}: 无法在 {label} 找到 "
                f"{media_item_label(media_item) or member.media_item_id}"
            )
    to_add = [item_id for item_id in wanted_ids if item_id not in remote_ids]
    to_remove = [item_id for item_id in remote_ids if item_id not in wanted_ids]
    added_ok, add_failed = 0, 0
    removed_ok, remove_failed = 0, 0
    if to_add:
        added_ok, add_failed = client.add_items_to_collection(collection.external_id, to_add)
    if to_remove:
        removed_ok, remove_failed = client.remove_items_from_collection(
            collection.external_id, to_remove
        )
    session.flush()
    boxset_items = client.get_collection_items(collection.external_id)
    _refresh_member_counts(
        session,
        collection,
        remote_item_count=len(boxset_items),
        touch_sync=True,
    )
    logger.info(
        f"    ✓ 合集 {collection.name}: 回写 {label} 新增 {added_ok} 项, "
        f"移除 {removed_ok} 项, 未对上 {unresolved} 项"
        + (f", 新增失败 {add_failed} 项" if add_failed else "")
        + (f", 移除失败 {remove_failed} 项" if remove_failed else "")
    )
    return collection


def add_collection_members(session, collection: Collection, media_item_ids: list) -> int:
    from bonita.modules.media_service.factory import get_media_client

    client = get_media_client(collection_source(collection))
    existing_ids = {
        row.media_item_id
        for row in session.query(CollectionItem.media_item_id).filter(
            CollectionItem.collection_id == collection.id
        ).all()
    }
    added = 0
    for media_item_id in dict.fromkeys(media_item_ids):
        if media_item_id in existing_ids:
            continue
        media_item = session.query(MediaItem).filter(MediaItem.id == media_item_id).first()
        if not media_item:
            continue
        remote_id = None
        if client:
            try:
                remote_id = find_remote_id_for_media_item(session, client, media_item)
            except Exception as e:
                logger.warning(f"    ⊘ 查找远端条目失败 {media_item.title}: {e}")
        session.add(
            CollectionItem(
                collection_id=collection.id,
                media_item_id=media_item.id,
                external_item_id=remote_id,
            )
        )
        existing_ids.add(media_item.id)
        added += 1
    session.flush()
    _refresh_member_counts(session, collection)
    return added


def remove_collection_member(session, collection: Collection, media_item_id: int) -> bool:
    row = session.query(CollectionItem).filter(
        CollectionItem.collection_id == collection.id,
        CollectionItem.media_item_id == media_item_id,
    ).first()
    if not row:
        return False
    session.delete(row)
    session.flush()
    _refresh_member_counts(session, collection)
    return True


def sync_whitelisted_collections(session, direction: str = "from_server") -> int:
    collections = session.query(Collection).all()
    if not collections:
        logger.info("  ⊘ 没有要同步的合集")
        return 0
    synced = 0
    for collection in collections:
        try:
            sync_collection_members(session, collection, direction=direction)
            synced += 1
        except Exception as e:
            logger.error(f"  ✗ 合集同步失败 {collection.name}: {e}")
    return synced
