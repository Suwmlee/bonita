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

        if direction == "to_emby":
            # Bonita → Emby: 将本地观看记录回写到 Emby
            logger.info("开始回写本地观看记录到 Emby")
            write_back_to_emby(session, emby_service)
        else:
            # Emby → Bonita: 从 Emby 同步观看记录到本地（默认）
            logger.info(f"开始从 Emby 同步观看记录到本地 (force={force})")
            watched_items = emby_service.get_user_all_items()

            if not watched_items:
                logger.info("Emby 中没有找到观看记录")
                return

            for library_id, library_items in watched_items.items():
                for item in library_items["movies"]:
                    try:
                        convert_emby_watched_items(session, item, force=force)
                    except Exception as e:
                        logger.error(f"Error converting Emby watched item: {e}")
                        continue
                # for item in library_items["episodes"]:
                #     convert_emby_watched_items(session, item, force=force)

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
        # 处理喜爱标记：以app记录为准，除非强制模式
        final_favorite = existing_record.favorite
        if force:
            final_favorite = is_favorite
        else:
            if existing_record.favorite:
                final_favorite = True
            else:
                final_favorite = is_favorite

        # 检查existing_record是否有实际变化
        has_record_changes = (
            existing_record.watched != watched or
            existing_record.watch_count != watch_count or
            existing_record.favorite != final_favorite or
            existing_record.play_progress != play_progress or
            existing_record.duration != duration
        )
        if has_record_changes:
            existing_record.watched = watched
            existing_record.watch_count = watch_count
            existing_record.favorite = final_favorite
            existing_record.play_progress = play_progress
            existing_record.duration = duration
            session.commit()
            logger.debug(f"Updated watch history for media_item {media_item.id}, favorite: {existing_record.favorite} -> {final_favorite}")
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
        logger.debug(f"Created new watch history for media_item {media_item.id}, favorite: {is_favorite}")


def write_back_to_emby(session, emby_service):
    """将本地观看记录回写到 Emby（仅针对有 number 的项目）
    
    Args:
        session: Database session
        emby_service: EmbyService 实例
    """
    try:
        if not emby_service or not emby_service.is_initialized:
            logger.info("EmbyService 未初始化，跳过回写")
            return

        # 只获取有 number 的观看记录
        watch_histories = session.query(WatchHistory, MediaItem).join(
            MediaItem, WatchHistory.media_item_id == MediaItem.id
        ).filter(MediaItem.number.isnot(None)).all()

        if not watch_histories:
            logger.info("没有找到需要回写的观看记录（仅处理有 number 的项目）")
            return

        # 获取 Emby 中的所有项目
        watched_items = emby_service.get_user_all_items()
        if not watched_items:
            logger.info("Emby 中没有找到任何项目")
            return

        # 建立 filepath 到 emby item 的映射
        emby_items_by_path = {}
        for library_id, library_items in watched_items.items():
            for item in library_items.get("movies", []):
                filepath = item.get("Path")
                if filepath:
                    emby_items_by_path[filepath] = item
            for item in library_items.get("episodes", []):
                filepath = item.get("Path")
                if filepath:
                    emby_items_by_path[filepath] = item

        updated_count = 0
        for watch_history, media_item in watch_histories:
            try:
                # 通过 number 找到对应的文件路径
                number = media_item.number
                if not number:
                    continue

                # 查找转移记录获取目标路径
                trans_record = session.query(TransRecords).join(
                    ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
                ).filter(ExtraInfo.number == number).first()

                if not trans_record or not trans_record.destpath:
                    logger.debug(f"找不到 number {number} 的转移记录")
                    continue

                destpath = trans_record.destpath
                emby_item = emby_items_by_path.get(destpath)

                if not emby_item:
                    logger.debug(f"在 Emby 中找不到文件路径: {destpath}")
                    continue

                # 获取 emby 中的当前状态
                item_id = emby_item.get("Id")
                user_data = emby_item.get("UserData", {})
                emby_watched = user_data.get("Played", False)
                emby_favorite = user_data.get("IsFavorite", False)

                # 比较状态并更新
                need_update = False
                
                # 处理观看状态
                if watch_history.watched and not emby_watched:
                    logger.info(f"标记 Emby 中的项目为已观看: {media_item.title} (number: {number})")
                    emby_service.mark_as_played(item_id)
                    need_update = True
                elif not watch_history.watched and emby_watched:
                    logger.info(f"标记 Emby 中的项目为未观看: {media_item.title} (number: {number})")
                    emby_service.mark_as_unplayed(item_id)
                    need_update = True
                
                # 处理喜爱状态
                if watch_history.favorite and not emby_favorite:
                    logger.info(f"标记 Emby 中的项目为喜爱: {media_item.title} (number: {number})")
                    emby_service.mark_as_favorite(item_id)
                    need_update = True
                elif not watch_history.favorite and emby_favorite:
                    logger.info(f"取消 Emby 中的项目喜爱: {media_item.title} (number: {number})")
                    emby_service.unmark_as_favorite(item_id)
                    need_update = True

                if need_update:
                    updated_count += 1

            except Exception as e:
                logger.error(f"回写 Emby 记录时出错 (media_item: {media_item.title}, number: {media_item.number}): {e}")
                continue

        logger.info(f"回写完成，共更新 {updated_count} 条记录")

    except Exception as e:
        logger.error(f"回写到 Emby 时出错: {e}")
        raise
