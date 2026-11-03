"""把转移记录挂到媒体项上。番号和 Emby 电影共用 TransRecords.media_item_id。"""
import logging
from typing import Optional

from sqlalchemy import func

from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.mediaitem import MediaItem
from bonita.db.models.metadata import Metadata
from bonita.db.models.record import TransRecords
from bonita.services.subtitle_service import normalize_number

logger = logging.getLogger(__name__)

NUMBER_MEDIA_TYPE = "number"


def metadata_for_number(session, number: str) -> Optional[Metadata]:
    key = normalize_number(number)
    if not key:
        return None
    expr = func.upper(func.trim(Metadata.number))
    return (
        session.query(Metadata)
        .filter(expr == key)
        .order_by(Metadata.id.desc())
        .first()
    )


def find_number_media_item(session, number: str) -> Optional[MediaItem]:
    """一个规范化番号只取一行。优先 media_type 为 number，其次尚未改类型的 movie。"""
    key = normalize_number(number)
    if not key:
        return None
    expr = func.upper(func.trim(MediaItem.number))
    rows = (
        session.query(MediaItem)
        .filter(
            expr == key,
            MediaItem.media_type.in_((NUMBER_MEDIA_TYPE, "movie")),
        )
        .order_by(MediaItem.id.desc())
        .all()
    )
    for row in rows:
        if row.media_type == NUMBER_MEDIA_TYPE:
            return row
    return rows[0] if rows else None


def ensure_number_media_item(session, number: str, title: str = "") -> Optional[MediaItem]:
    key = normalize_number(number)
    if not key:
        return None
    display = (title or "").strip() or key
    item = find_number_media_item(session, key)
    if item:
        if item.media_type != NUMBER_MEDIA_TYPE:
            item.media_type = NUMBER_MEDIA_TYPE
        if normalize_number(item.number) != key:
            item.number = key
        if display and item.title != display:
            item.title = display
        return item
    item = MediaItem(media_type=NUMBER_MEDIA_TYPE, title=display, number=key)
    session.add(item)
    session.flush()
    logger.info("    ✓ 创建番号媒体项: %s (%s)", display, key)
    return item


def media_item_for_numbered_record(session, record, create: bool = False) -> Optional[MediaItem]:
    """记录上的番号已经刮进 metadata 时，返回对应媒体项。

    create 为真时，metadata 在但媒体项还没有，就建一行。改番号的保存路径不建。
    番号为空、而当前挂的是番号媒体项时，把那一行返回，供调用方决定是否保留。
    """
    if not record:
        return None
    extra = session.query(ExtraInfo).filter(ExtraInfo.filepath == record.srcpath).first()
    number = normalize_number(extra.number) if extra and extra.number else ""
    if number:
        meta = metadata_for_number(session, number)
        if not meta:
            return None
        if not create and not find_number_media_item(session, number):
            return None
        return ensure_number_media_item(session, number, meta.title or number)
    if record.media_item_id:
        current = session.query(MediaItem).filter(MediaItem.id == record.media_item_id).first()
        if current and current.media_type == NUMBER_MEDIA_TYPE:
            return current
    return None


def link_records_with_number(session, number: str, media_item: MediaItem) -> int:
    key = normalize_number(number)
    if not key or not media_item:
        return 0
    expr = func.upper(func.trim(ExtraInfo.number))
    records = (
        session.query(TransRecords)
        .join(ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath)
        .filter(expr == key)
        .all()
    )
    changed = 0
    for record in records:
        if record.media_item_id != media_item.id:
            record.media_item_id = media_item.id
            changed += 1
    return changed


def attach_number_records(session, number: str, title: str = "") -> None:
    """metadata 已在库里时，确保番号媒体项，并把该番号的记录都指过去。"""
    key = normalize_number(number)
    if not key:
        return
    try:
        meta = metadata_for_number(session, key)
        if not meta:
            return
        item = ensure_number_media_item(session, key, meta.title or title or key)
        if not item:
            return
        link_records_with_number(session, key, item)
        session.commit()
    except Exception:
        logger.exception("挂接番号媒体项失败: %s", key)
        session.rollback()


def relink_record_for_number(session, record, number: str) -> None:
    """按保存后的番号重挂这一条记录，不新建媒体项。"""
    if not record:
        return
    key = normalize_number(number)
    if key:
        item = find_number_media_item(session, key)
        meta = metadata_for_number(session, key)
        if item and meta:
            record.media_item_id = ensure_number_media_item(session, key, meta.title or key).id
        else:
            record.media_item_id = None
        return
    if not record.media_item_id:
        return
    current = session.query(MediaItem).filter(MediaItem.id == record.media_item_id).first()
    if current and current.media_type == NUMBER_MEDIA_TYPE:
        record.media_item_id = None
