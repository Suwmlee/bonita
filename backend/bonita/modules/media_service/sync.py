import logging

from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.metadata import Metadata
from bonita.db.models.record import TransRecords
from bonita.db.models.mediaitem import MediaItem
from bonita.db.models.watch_history import WatchHistory
from bonita.modules.media_service.emby import EmbyService
from bonita.modules.scraping.number_parser import get_number


logger = logging.getLogger(__name__)


def sync_emby_history(session, direction="from_emby", force=False):
    """同步 Emby 和 Bonita 之间的观看记录

    Args:
        session: Database session
        direction (str): 同步方向
            - "from_emby": 从 Emby 同步到 Bonita（默认）
            - "to_emby": 从 Bonita 回写到 Emby
        force (bool): 是否强制覆盖数据
            - direction="from_emby" 时：是否强制覆盖本地数据（包括喜爱标记）
            - direction="to_emby" 时：当前未使用

    Returns:
        None
    """
    try:
        emby_service = EmbyService()
        if not emby_service.is_initialized:
            logger.info("EmbyService未初始化，跳过同步")
            return

        # 统一获取 Emby 中的所有项目
        watched_items = emby_service.get_user_all_items()
        if not watched_items:
            logger.info("Emby 中没有找到任何项目")
            return

        for library_id, library_items in watched_items.items():
            for item in library_items.get("movies", []):
                try:
                    if direction == "to_emby":
                        sync_item_to_emby(session, emby_service, item, force)
                    else:
                        convert_emby_watched_items(session, item, force)
                except Exception as e:
                    logger.error(f"Error processing sync Emby item: {e}")
                    continue
            # for item in library_items.get("episodes", []):
            #     try:
            #         if direction == "to_emby":
            #             sync_item_to_emby(session, emby_service, item)
            #         else:
            #             convert_emby_watched_items(session, item, force=force)
            #     except Exception as e:
            #         logger.error(f"Error processing Emby item: {e}")
            #         continue

        return

    except Exception as e:
        logger.error(f"Error syncing Emby history: {e}")
        raise


def convert_emby_watched_items(session, item, force=False):
    """Convert Emby watched items to a list of dictionaries

    Args:
        session: Database session
        item: Emby item data
        force: 是否强制覆盖本地数据（包括喜爱标记）
    """
    # Extract item data
    item_id = item.get("Id", "")
    if not item_id:
        return None

    # Determine content type
    content_type = "movie"
    if item.get("Type") == "Episode":
        content_type = "episode"

    # Extract metadata
    title = item.get("Name", "")
    original_title = item.get("OriginalTitle", "")
    duration = 0
    if "RunTimeTicks" in item and item["RunTimeTicks"] > 0:
        duration = int(item["RunTimeTicks"] / 10000000)

    user_data = item.get("UserData", {})
    watched = user_data.get("Played", False)
    is_favorite = user_data.get("IsFavorite", False)
    watch_count = user_data.get("PlayCount", 1)
    play_progress = 100.0 if watched else 0.0
    if "PlaybackPositionTicks" in user_data and user_data["PlaybackPositionTicks"] > 0:
        position_seconds = int(user_data["PlaybackPositionTicks"] / 10000000)
        play_progress = min(100.0, (position_seconds / duration) * 100)

    # Extract external IDs
    provider_ids = item.get("ProviderIds", {})
    imdb_id = provider_ids.get("Imdb", "")
    tmdb_id = provider_ids.get("Tmdb", "")
    tvdb_id = provider_ids.get("Tvdb", "")

    # 查找或创建MediaItem
    media_item = None

    if len(provider_ids):
        # 有提供商ID，按提供商ID查找
        if imdb_id:
            media_item = session.query(MediaItem).filter(MediaItem.imdb_id == imdb_id).first()
        if not media_item and tmdb_id:
            media_item = session.query(MediaItem).filter(MediaItem.tmdb_id == tmdb_id).first()
        if not media_item and tvdb_id:
            media_item = session.query(MediaItem).filter(MediaItem.tvdb_id == tvdb_id).first()
        if media_item:
            # 检查media_item是否有实际变化
            has_media_changes = (
                media_item.media_type != content_type or
                media_item.title != title or
                media_item.original_title != original_title or
                media_item.imdb_id != imdb_id or
                media_item.tmdb_id != tmdb_id or
                media_item.tvdb_id != tvdb_id
            )
            if has_media_changes:
                media_item.media_type = content_type
                media_item.title = title
                media_item.original_title = original_title
                media_item.imdb_id = imdb_id
                media_item.tmdb_id = tmdb_id
                media_item.tvdb_id = tvdb_id
                session.commit()
        else:
            media_item = MediaItem(
                media_type=content_type,
                title=title,
                original_title=original_title,
                imdb_id=imdb_id,
                tmdb_id=tmdb_id,
                tvdb_id=tvdb_id,
            )
            media_item.create(session)
    else:
        filepath = item.get("Path")
        # Extract number from filepath - first try database, then fallback to parsing
        number = None
        result = session.query(TransRecords, ExtraInfo).outerjoin(
            ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
        ).filter(TransRecords.destpath == filepath).first()
        if result and result[1]:
            number = result[1].number
        else:
            number = get_number(filepath)
        if not number:
            return None
        meta_and_item = session.query(Metadata, MediaItem).outerjoin(
            MediaItem, MediaItem.number == Metadata.number
        ).filter(Metadata.number == number).first()

        if not meta_and_item or not meta_and_item[0]:
            logger.debug(f"No metadata found for number: {number}")
            return None
        meta = meta_and_item[0]
        media_item = meta_and_item[1]
        if media_item:
            if media_item.title != meta.title:
                media_item.title = meta.title
                session.commit()
        else:
            media_item = MediaItem(
                media_type=content_type,
                title=meta.title,
                number=number,
            )
            media_item.create(session)

    existing_record = session.query(WatchHistory).filter(WatchHistory.media_item_id == media_item.id).first()
    if existing_record:
        # 处理观看/喜爱状态：本地记录优先级更高，除非强制模式
        final_watched = watched if force else (existing_record.watched or watched)
        final_favorite = is_favorite if force else (existing_record.favorite or is_favorite)

        # 检查existing_record是否有实际变化
        has_record_changes = (
            existing_record.watched != final_watched or
            existing_record.watch_count != watch_count or
            existing_record.favorite != final_favorite or
            existing_record.play_progress != play_progress or
            existing_record.duration != duration
        )
        if has_record_changes:
            existing_record.watched = final_watched
            existing_record.watch_count = watch_count
            existing_record.favorite = final_favorite
            existing_record.play_progress = play_progress
            existing_record.duration = duration
            session.commit()
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


def sync_item_to_emby(session, emby_service, item, force=False):
    """将单个 Emby item 对应的本地观看记录回写到 Emby（仅针对有 number 的项目）

    Args:
        session: Database session
        emby_service: EmbyService 实例
        item: Emby item 数据
        force: 是否强制以 Bonita 为准
            - True: 强制以 Bonita 的状态为准，覆盖 Emby 的状态
            - False: 当 Bonita 未观看/未喜爱而 Emby 已观看/已喜爱时，保持 Emby 的状态不更新

    Returns:
        bool: 是否更新了记录
    """
    # 获取 item 的 filepath
    filepath = item.get("Path")
    if not filepath:
        return False

    # 通过 filepath 找到对应的 number
    result = session.query(TransRecords, ExtraInfo).join(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
    ).filter(TransRecords.destpath == filepath).first()

    if not result or not result[1]:
        return False

    number = result[1].number
    if not number:
        return False

    # 通过 number 找到对应的 media_item 和 watch_history
    watch_data = session.query(WatchHistory, MediaItem).join(
        MediaItem, WatchHistory.media_item_id == MediaItem.id
    ).filter(MediaItem.number == number).first()

    if not watch_data:
        return False

    watch_history, media_item = watch_data

    item_id = item.get("Id")
    user_data = item.get("UserData", {})
    emby_watched = user_data.get("Played", False)
    emby_favorite = user_data.get("IsFavorite", False)

    # 处理观看状态
    if watch_history.watched and not emby_watched:
        emby_service.mark_as_played(item_id)
    elif not watch_history.watched and emby_watched:
        if force:
            # force 模式：以 bonita 为准，将 emby 标记为未观看
            logger.info(f"标记 Emby 中的项目为未观看 (force): {media_item.title} (number: {number})")
            emby_service.mark_as_unplayed(item_id)

    # 处理喜爱状态
    if watch_history.favorite and not emby_favorite:
        emby_service.mark_as_favorite(item_id)
    elif not watch_history.favorite and emby_favorite:
        if force:
            # force 模式：以 bonita 为准，取消 emby 的喜爱
            logger.info(f"取消 Emby 中的项目喜爱 (force): {media_item.title} (number: {number})")
            emby_service.unmark_as_favorite(item_id)
