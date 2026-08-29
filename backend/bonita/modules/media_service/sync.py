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
            - "to_emby": 从 Bonita 回写到 Emby（电影、剧集、番号）
        force (bool): 是否强制覆盖数据
            - direction="from_emby" 时：是否强制覆盖本地数据（包括喜爱标记）
            - direction="to_emby" 时：是否强制覆盖 Emby 上的已看/收藏状态

    Returns:
        None
    """
    try:
        emby_service = EmbyService()
        if not emby_service.is_initialized:
            logger.warning("  ⊘ Emby服务未初始化")
            return

        logger.info("  → 获取Emby媒体项目...")
        watched_items = emby_service.get_user_all_items()
        if not watched_items:
            logger.info("  ⊘ Emby 中没有媒体项目")
            return

        total_movies = sum(len(lib.get("movies", [])) for lib in watched_items.values())
        total_series = sum(len(lib.get("series", [])) for lib in watched_items.values())
        total_seasons = sum(len(lib.get("seasons", [])) for lib in watched_items.values())
        total_episodes = sum(len(lib.get("episodes", [])) for lib in watched_items.values())
        logger.info(
            f"  找到 {total_movies} 个电影, {total_series} 部剧, "
            f"{total_seasons} 季, {total_episodes} 集"
        )

        processed = 0
        synced = 0
        for library_items in watched_items.values():
            for item in (
                library_items.get("series", [])
                + library_items.get("movies", [])
                + library_items.get("episodes", [])
                + library_items.get("seasons", [])
            ):
                try:
                    processed += 1
                    if direction == "to_emby":
                        result = sync_item_to_emby(session, emby_service, item, force)
                        if result:
                            synced += 1
                    else:
                        convert_emby_watched_items(session, item, force)
                        synced += 1
                except Exception as e:
                    logger.error(f"  ✗ 处理项目失败: {e}")
                    continue

        logger.info(f"  ✓ 同步完成 - 处理:{processed} 同步:{synced}")
        return

    except Exception as e:
        logger.error(f"  ✗ Emby同步失败: {e}")
        raise


def convert_emby_watched_items(session, item, force=False):
    """将单个 Emby item 同步为本地 MediaItem + WatchHistory。"""
    if not item.get("Id"):
        return None

    if item.get("Type") == "Season":
        _propagate_season_favorite(session, item, force)
        return None

    media_item = _resolve_media_item(session, item, create=True)
    if not media_item:
        return None

    title = media_item.title
    duration = _ticks_to_seconds(item.get("RunTimeTicks"))
    user_data = item.get("UserData") or {}
    watched = bool(user_data.get("Played", False))
    is_favorite = bool(user_data.get("IsFavorite", False))
    if media_item.media_type == "episode" and media_item.series_id:
        parent_history = session.query(WatchHistory).filter(
            WatchHistory.media_item_id == media_item.series_id
        ).first()
        if parent_history and parent_history.favorite:
            is_favorite = True
    watch_count = user_data.get("PlayCount") or 1
    play_progress = 100.0 if watched else 0.0
    position_ticks = user_data.get("PlaybackPositionTicks") or 0
    if position_ticks > 0 and duration > 0:
        play_progress = min(100.0, (_ticks_to_seconds(position_ticks) / duration) * 100)

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
        _propagate_favorite_to_episodes(session, media_item.id)


def sync_item_to_emby(session, emby_service, item, force=False):
    """将单个 Emby item 对应的本地观看记录回写到 Emby。"""
    media_item = _resolve_media_item(session, item, create=False)
    if not media_item:
        return False

    watch_history = session.query(WatchHistory).filter(
        WatchHistory.media_item_id == media_item.id
    ).first()
    if not watch_history:
        return False

    item_id = item.get("Id")
    user_data = item.get("UserData") or {}
    emby_watched = user_data.get("Played", False)
    emby_favorite = user_data.get("IsFavorite", False)
    label = media_item.number or media_item.title

    updated = False
    if watch_history.watched and not emby_watched:
        emby_service.mark_as_played(item_id)
        logger.info(f"    ✓ 标记为已观看: {label}")
        updated = True
    elif not watch_history.watched and emby_watched and force:
        emby_service.mark_as_unplayed(item_id)
        logger.info(f"    ✓ 标记为未观看: {label}")
        updated = True

    if watch_history.favorite and not emby_favorite:
        emby_service.mark_as_favorite(item_id)
        logger.info(f"    ♥ 标记为喜爱: {label}")
        updated = True
    elif not watch_history.favorite and emby_favorite and force:
        emby_service.unmark_as_favorite(item_id)
        logger.info(f"    ✓ 取消喜爱: {label}")
        updated = True

    return updated


def _resolve_media_item(session, item, create=True):
    item_type = item.get("Type")
    if item_type == "Episode":
        return _resolve_episode(session, item, create)
    if item_type == "Series":
        record, _extra = _find_transfer_record(session, item.get("Path"))
        return _ensure_series(session, item, record, create)
    return _resolve_movie(session, item, create)


def _resolve_movie(session, item, create=True):
    title = item.get("Name") or ""
    original_title = item.get("OriginalTitle") or ""
    imdb_id, tmdb_id, tvdb_id = _provider_ids(item)

    media_item = _find_by_provider_ids(session, "movie", imdb_id, tmdb_id, tvdb_id)
    if media_item:
        _update_media_fields(
            session,
            media_item,
            media_type="movie",
            title=title,
            original_title=original_title,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
            tvdb_id=tvdb_id,
        )
        return media_item

    filepath = item.get("Path")
    number = None
    _record, extra = _find_transfer_record(session, filepath)
    if extra and extra.number:
        number = extra.number
    elif filepath:
        number = get_number(filepath)

    if number:
        meta_and_item = session.query(Metadata, MediaItem).outerjoin(
            MediaItem, MediaItem.number == Metadata.number
        ).filter(Metadata.number == number).first()
        if meta_and_item and meta_and_item[0]:
            meta = meta_and_item[0]
            media_item = meta_and_item[1]
            if media_item:
                if media_item.title != meta.title:
                    media_item.title = meta.title
                    session.commit()
                return media_item
            if create:
                media_item = MediaItem(
                    media_type="movie",
                    title=meta.title,
                    number=number,
                )
                media_item.create(session)
                logger.info(f"    ✓ 创建媒体项: {meta.title} ({number})")
                return media_item

    if not create or not (imdb_id or tmdb_id or tvdb_id):
        if number:
            logger.debug(f"    ⊘ 未找到元数据: {number}")
        return None

    media_item = MediaItem(
        media_type="movie",
        title=title,
        original_title=original_title,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id,
        tvdb_id=tvdb_id,
    )
    media_item.create(session)
    logger.debug(f"    ✓ 创建媒体项: {title}")
    return media_item


def _resolve_episode(session, item, create=True):
    record, _extra = _find_transfer_record(session, item.get("Path"))
    season = _as_int(item.get("ParentIndexNumber"), -1)
    episode_no = _as_int(item.get("IndexNumber"), -1)
    if record:
        if season < 0 and record.season is not None:
            season = record.season
        if episode_no < 0 and record.episode is not None:
            episode_no = record.episode

    # 剧场版/特典等挂在剧下但没有季集号，不能当正集写入，否则每次同步都会再复制一张「剧集」卡片
    if season < 0 or episode_no < 0:
        logger.debug("    ⊘ 缺少季/集编号，跳过")
        return None

    series = _ensure_series(session, item, record, create)
    imdb_id, tmdb_id, tvdb_id = _provider_ids(item)
    episode_title = item.get("Name") or ""
    series_name = (item.get("SeriesName") or "").strip()
    if not series_name and record and record.top_folder:
        series_name = record.top_folder
    if series and series.title:
        series_name = series.title

    if series and season >= 0 and episode_no >= 0:
        media_item = session.query(MediaItem).filter(
            MediaItem.media_type == "episode",
            MediaItem.series_id == series.id,
            MediaItem.season_number == season,
            MediaItem.episode_number == episode_no,
        ).first()
        if media_item:
            _update_media_fields(
                session,
                media_item,
                media_type="episode",
                title=episode_title or media_item.title,
                original_title=series_name or media_item.original_title,
                imdb_id=imdb_id or media_item.imdb_id,
                tmdb_id=tmdb_id or media_item.tmdb_id,
                tvdb_id=tvdb_id or media_item.tvdb_id,
                series_id=series.id,
                season_number=season,
                episode_number=episode_no,
            )
            return media_item

    media_item = _find_by_provider_ids(
        session, "episode", imdb_id, tmdb_id, tvdb_id, season, episode_no
    )
    if media_item:
        _update_media_fields(
            session,
            media_item,
            media_type="episode",
            title=episode_title or media_item.title,
            original_title=series_name or media_item.original_title,
            imdb_id=imdb_id or media_item.imdb_id,
            tmdb_id=tmdb_id or media_item.tmdb_id,
            tvdb_id=tvdb_id or media_item.tvdb_id,
            series_id=series.id if series else media_item.series_id,
            season_number=season if season >= 0 else media_item.season_number,
            episode_number=episode_no if episode_no >= 0 else media_item.episode_number,
        )
        return media_item

    if not create:
        return None
    if not episode_title and not (series and season >= 0 and episode_no >= 0):
        logger.debug("    ⊘ 剧集信息不足，跳过")
        return None

    media_item = MediaItem(
        media_type="episode",
        title=episode_title or f"S{season:02d}E{episode_no:02d}",
        original_title=series_name or None,
        imdb_id=imdb_id or None,
        tmdb_id=tmdb_id or None,
        tvdb_id=tvdb_id or None,
        series_id=series.id if series else None,
        season_number=season,
        episode_number=episode_no,
    )
    media_item.create(session)
    logger.info(f"    ✓ 创建剧集: {series_name} S{season:02d}E{episode_no:02d} {episode_title}")
    return media_item


def _ensure_series(session, item, record, create=True):
    if item.get("Type") == "Series":
        series_name = (item.get("Name") or item.get("SeriesName") or "").strip()
    else:
        series_name = (item.get("SeriesName") or item.get("Name") or "").strip()
    if not series_name and record and record.top_folder:
        series_name = record.top_folder.strip()

    if series_name:
        media_item = session.query(MediaItem).filter(
            MediaItem.media_type == "tvshow",
            MediaItem.title == series_name,
        ).first()
        if media_item and (media_item.imdb_id or media_item.tmdb_id):
            return media_item

    imdb_id = tmdb_id = tvdb_id = ""
    original_title = ""
    series_emby_id = item.get("SeriesId")
    if item.get("Type") == "Series":
        series_emby_id = item.get("Id") or series_emby_id
    if series_emby_id:
        details = _get_emby_item_details(series_emby_id)
        if details:
            imdb_id, tmdb_id, tvdb_id = _provider_ids(details)
            series_name = (details.get("Name") or series_name).strip()
            original_title = details.get("OriginalTitle") or ""

    media_item = _find_by_provider_ids(session, "tvshow", imdb_id, tmdb_id, tvdb_id)
    if not media_item and series_name:
        media_item = session.query(MediaItem).filter(
            MediaItem.media_type == "tvshow",
            MediaItem.title == series_name,
        ).first()
    if media_item:
        _update_media_fields(
            session,
            media_item,
            media_type="tvshow",
            title=series_name or media_item.title,
            original_title=original_title or media_item.original_title,
            imdb_id=imdb_id or media_item.imdb_id,
            tmdb_id=tmdb_id or media_item.tmdb_id,
            tvdb_id=tvdb_id or media_item.tvdb_id,
        )
        return media_item
    if not create or not series_name:
        return None

    media_item = MediaItem(
        media_type="tvshow",
        title=series_name,
        original_title=original_title or None,
        imdb_id=imdb_id or None,
        tmdb_id=tmdb_id or None,
        tvdb_id=tvdb_id or None,
    )
    media_item.create(session)
    logger.info(f"    ✓ 创建剧集父项: {series_name}")
    return media_item


def _propagate_season_favorite(session, item, force=False):
    user_data = item.get("UserData") or {}
    is_favorite = bool(user_data.get("IsFavorite", False))
    if not is_favorite and not force:
        return
    record, _extra = _find_transfer_record(session, item.get("Path"))
    series = _ensure_series(session, item, record, create=True)
    if not series:
        return
    season = _as_int(item.get("IndexNumber"), -1)
    if season < 0:
        return
    if is_favorite:
        _propagate_favorite_to_episodes(session, series.id, season)
        logger.info(f"    ♥ 季收藏已同步到各集: {series.title} S{season:02d}")


def _propagate_favorite_to_episodes(session, series_id, season=None):
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


def _find_by_provider_ids(
    session,
    media_type,
    imdb_id="",
    tmdb_id="",
    tvdb_id="",
    season=None,
    episode_no=None,
):
    query = session.query(MediaItem).filter(MediaItem.media_type == media_type)
    if media_type == "episode":
        if season is not None and season >= 0:
            query = query.filter(MediaItem.season_number == season)
        if episode_no is not None and episode_no >= 0:
            query = query.filter(MediaItem.episode_number == episode_no)
    if imdb_id:
        found = query.filter(MediaItem.imdb_id == imdb_id).first()
        if found:
            return found
    if tmdb_id:
        found = query.filter(MediaItem.tmdb_id == tmdb_id).first()
        if found:
            return found
    if tvdb_id:
        found = query.filter(MediaItem.tvdb_id == tvdb_id).first()
        if found:
            return found
    return None


def _update_media_fields(session, media_item, **fields):
    changed = False
    for key, value in fields.items():
        if value in (None, "") and getattr(media_item, key, None) not in (None, "", -1):
            continue
        if getattr(media_item, key, None) != value:
            setattr(media_item, key, value)
            changed = True
    if changed:
        session.commit()


def _find_transfer_record(session, filepath):
    if not filepath:
        return None, None
    result = session.query(TransRecords, ExtraInfo).outerjoin(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
    ).filter(TransRecords.destpath == filepath).first()
    if not result:
        return None, None
    return result[0], result[1]


def _provider_ids(item):
    provider_ids = item.get("ProviderIds") or {}
    return (
        provider_ids.get("Imdb") or "",
        str(provider_ids.get("Tmdb") or ""),
        provider_ids.get("Tvdb") or "",
    )


def _as_int(value, default=-1):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ticks_to_seconds(ticks):
    if not ticks:
        return 0
    try:
        ticks = int(ticks)
    except (TypeError, ValueError):
        return 0
    if ticks <= 0:
        return 0
    return int(ticks / 10000000)


def _get_emby_item_details(item_id):
    if not item_id:
        return None
    try:
        emby_service = EmbyService()
        if not emby_service.is_initialized:
            from bonita.core.service import init_emby
            init_emby()
        if not emby_service.is_initialized:
            return None
        details = emby_service.get_item_details(item_id)
        return details if isinstance(details, dict) else None
    except Exception as e:
        logger.warning(f"  ⊘ 获取 Emby 项目详情失败: {e}")
        return None


def _get_emby_user_item_details(item_id):
    if not item_id:
        return None
    try:
        emby_service = EmbyService()
        if not emby_service.is_initialized:
            from bonita.core.service import init_emby
            init_emby()
        if not emby_service.is_initialized:
            return None
        details = emby_service.get_user_item_details(item_id)
        return details if isinstance(details, dict) else None
    except Exception as e:
        logger.warning(f"  ⊘ 获取 Emby 用户条目失败: {e}")
        return None


_WEBHOOK_WATCH_EVENTS = {
    "playback.stop",
    "playback.scrobble",
    "item.markplayed",
    "item.markunplayed",
    "item.rate",
}
_WEBHOOK_LIBRARY_EVENTS = {
    "library.new",
    "item.added",
}
_SYNCABLE_ITEM_TYPES = {"Movie", "Video", "Episode", "Series", "Season"}


def handle_emby_webhook_event(session, payload: dict) -> str:
    """处理 Emby Webhook：观看状态变更，以及新媒体入库。"""
    if not isinstance(payload, dict):
        return "ignored"

    event = str(payload.get("Event") or payload.get("event") or "").strip().lower()
    if event == "system.webhooktest":
        logger.info("  ✓ 收到 Emby Webhook 测试事件")
        return "test"
    if event not in _WEBHOOK_WATCH_EVENTS and event not in _WEBHOOK_LIBRARY_EVENTS:
        return "ignored"

    setting_user = _get_configured_emby_user(session)
    webhook_user = (payload.get("User") or {}).get("Name") or ""
    if (
        event in _WEBHOOK_WATCH_EVENTS
        and setting_user
        and webhook_user
        and webhook_user.lower() != setting_user.lower()
    ):
        logger.info(f"  ⊘ 忽略其他用户的 Webhook: {webhook_user}")
        return "skipped"

    items = _extract_webhook_items(payload)
    if not items:
        logger.warning("  ⊘ Webhook 缺少 Item")
        return "ignored"

    synced = 0
    for item in items:
        if not _is_syncable_webhook_item(item):
            continue
        item = _enrich_webhook_item(item)
        if event in _WEBHOOK_LIBRARY_EVENTS:
            convert_emby_watched_items(session, item, force=False)
            logger.info(f"  ✓ Webhook 新媒体入库: {item.get('Name')}")
            synced += 1
            continue

        user_data = item.setdefault("UserData", {})
        if not isinstance(user_data, dict):
            user_data = {}
            item["UserData"] = user_data

        playback_info = payload.get("PlaybackInfo") or {}
        played_to_completion = bool(playback_info.get("PlayedToCompletion"))

        if event == "item.rate":
            details = _get_emby_user_item_details(item.get("Id"))
            user_data_from_emby = details.get("UserData") if isinstance(details, dict) else None
            if not isinstance(user_data_from_emby, dict):
                logger.warning(f"  ⊘ item.rate 无法获取收藏状态: {item.get('Name')}")
                continue
            item = {**item, **details}
            item["UserData"] = user_data_from_emby
            convert_emby_watched_items(session, item, force=True)
            logger.info(
                f"  ✓ Webhook 同步收藏: {item.get('Name')} "
                f"favorite={bool(user_data_from_emby.get('IsFavorite'))}"
            )
        elif event == "item.markunplayed":
            user_data["Played"] = False
            convert_emby_watched_items(session, item, force=True)
            logger.info(f"  ✓ Webhook 标记未观看: {item.get('Name')}")
        else:
            if event == "item.markplayed" or played_to_completion:
                user_data["Played"] = True
            convert_emby_watched_items(session, item, force=False)
            logger.info(f"  ✓ Webhook 同步观看状态: {event} {item.get('Name')}")
        synced += 1

    return "synced" if synced else "ignored"


def _extract_webhook_items(payload: dict) -> list:
    items = []
    raw_item = payload.get("Item") or payload.get("item")
    if isinstance(raw_item, dict):
        items.append(raw_item)
    raw_items = payload.get("Items") or payload.get("items")
    if isinstance(raw_items, list):
        items.extend(item for item in raw_items if isinstance(item, dict))
    return [item for item in items if item.get("Id")]


def _is_syncable_webhook_item(item: dict) -> bool:
    item_type = item.get("Type") or ""
    if item_type in ("Series", "Season"):
        return True
    if item.get("IsFolder"):
        return False
    return item_type in _SYNCABLE_ITEM_TYPES or not item_type


def _get_configured_emby_user(session) -> str:
    from bonita.services.setting_service import SettingService

    settings = SettingService(session).get_emby_settings()
    return settings.get("emby_user") or ""


def _enrich_webhook_item(item: dict) -> dict:
    """Webhook 载荷经常缺 Path / ProviderIds / 季集信息，必要时向 Emby 补全。"""
    needs_enrich = (
        not item.get("Path")
        or not item.get("ProviderIds")
        or (
            item.get("Type") == "Episode"
            and (
                item.get("ParentIndexNumber") is None
                or item.get("IndexNumber") is None
                or not item.get("SeriesName")
            )
        )
    )
    if not needs_enrich:
        return item
    details = _get_emby_item_details(item.get("Id"))
    if not details:
        return item
    merged = {**details, **item}
    for key in ("Path", "ProviderIds", "UserData", "SeriesName", "SeriesId",
                "ParentIndexNumber", "IndexNumber", "RunTimeTicks"):
        if not merged.get(key) and details.get(key) is not None:
            merged[key] = details.get(key)
    return merged
