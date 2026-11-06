import logging
import os

from bonita.db.models.collection import Collection, CollectionItem
from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.record import TransRecords
from bonita.db.models.mediaitem import MediaItem
from bonita.modules.media_service.client import (
    ITEM_EPISODE,
    ITEM_MOVIE,
    ITEM_SERIES,
    ITEM_VIDEO,
    MediaServerClient,
    RemoteItem,
)
from bonita.modules.media_service.record_link import (
    ensure_number_media_item,
    media_item_for_numbered_record,
    metadata_for_number,
)
from bonita.modules.scraping.number_parser import get_number, version_suffix_for

logger = logging.getLogger(__name__)

UNLINKED_VIDEO_TYPE = "video"
_UNLINKED_VIDEO_TYPES = {ITEM_MOVIE, ITEM_VIDEO}


def is_blank(value) -> bool:
    return value is None or str(value).strip() == ""


def has_external_ids(imdb_id=None, tmdb_id=None, tvdb_id=None) -> bool:
    return not (is_blank(imdb_id) and is_blank(tmdb_id) and is_blank(tvdb_id))


def requires_external_ids(media_type: str, number: str = None) -> bool:
    """电影（无番号）和电视剧必须带有 IMDB / TMDB / TVDB 之一。"""
    if media_type == "tvshow":
        return True
    if media_type == "movie" and is_blank(number):
        return True
    return False


def resolve_media_item(session, item: RemoteItem, client: MediaServerClient, create=True):
    if item.item_type == ITEM_EPISODE:
        media_item = _resolve_episode(session, item, client, create)
    elif item.item_type == ITEM_SERIES:
        record, _extra = find_transfer_record(session, item.path)
        return ensure_series(session, item, record, client, create)
    else:
        media_item = _resolve_movie(session, item, create)
    if media_item and item.item_type in (ITEM_MOVIE, ITEM_VIDEO, ITEM_EPISODE):
        link_remote_files(session, item, media_item)
    return media_item


def resolve_collection_member(session, item: RemoteItem, client: MediaServerClient):
    media_item = resolve_media_item(session, item, client, create=False)
    if media_item:
        return media_item
    if item.item_type not in _UNLINKED_VIDEO_TYPES:
        return None
    return create_unlinked_video(session, item)


def create_unlinked_video(session, item: RemoteItem) -> MediaItem:
    title = (item.title or "").strip() or item.remote_id or "未命名视频"
    original_title = (item.original_title or "").strip() or None
    media_item = MediaItem(
        media_type=UNLINKED_VIDEO_TYPE,
        title=title,
        original_title=original_title,
    )
    media_item.create(session)
    logger.info(f"    ✓ 创建无关联视频: {title}")
    return media_item


def find_media_item_by_remote_id(session, remote_id: str, source: str = None):
    if not remote_id:
        return None
    query = session.query(CollectionItem).filter(
        CollectionItem.external_item_id == remote_id
    )
    if source:
        query = query.join(Collection, Collection.id == CollectionItem.collection_id).filter(
            Collection.source == source
        )
    row = query.first()
    if not row:
        return None
    return session.query(MediaItem).filter(MediaItem.id == row.media_item_id).first()


def find_transfer_record(session, filepath):
    if not filepath:
        return None, None
    result = session.query(TransRecords, ExtraInfo).outerjoin(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
    ).filter(TransRecords.destpath == filepath).first()
    if not result:
        return None, None
    return result[0], result[1]


def find_by_provider_ids(
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


def update_media_fields(session, media_item, **fields):
    changed = False
    for key, value in fields.items():
        if value in (None, "") and getattr(media_item, key, None) not in (None, "", -1):
            continue
        if getattr(media_item, key, None) != value:
            setattr(media_item, key, value)
            changed = True
    if changed:
        session.commit()
    return changed


def _provider_id_pairs(media_item: MediaItem, remote: RemoteItem):
    return (
        (media_item.imdb_id, remote.imdb_id),
        (media_item.tmdb_id, remote.tmdb_id),
        (media_item.tvdb_id, remote.tvdb_id),
    )


def _ids_compatible(media_item: MediaItem, remote: RemoteItem) -> bool:
    return all(
        is_blank(local) or is_blank(remote_id) or str(local) == str(remote_id)
        for local, remote_id in _provider_id_pairs(media_item, remote)
    )


def _has_shared_provider_id(media_item: MediaItem, remote: RemoteItem) -> bool:
    return any(
        not is_blank(local) and not is_blank(remote_id) and str(local) == str(remote_id)
        for local, remote_id in _provider_id_pairs(media_item, remote)
    )


def _titles_match(media_item: MediaItem, remote: RemoteItem) -> bool:
    local = (media_item.title or "").strip().lower()
    remote_title = (remote.title or "").strip().lower()
    if local and remote_title and local == remote_title:
        return True
    original = (media_item.original_title or "").strip().lower()
    return bool(original and remote_title and original == remote_title)


def fill_blank_external_ids(session, media_item: MediaItem, remote: RemoteItem) -> bool:
    """路径已经对上时补空编号，不要求标题相同，也不覆盖已有编号。"""
    if not media_item or not remote or not _ids_compatible(media_item, remote):
        return False
    return update_media_fields(
        session,
        media_item,
        imdb_id=remote.imdb_id or media_item.imdb_id,
        tmdb_id=remote.tmdb_id or media_item.tmdb_id,
        tvdb_id=remote.tvdb_id or media_item.tvdb_id,
    )


def fill_blank_provider_ids(session, media_item: MediaItem, remote: RemoteItem) -> bool:
    """只补空的 IMDb/TMDB/TVDB，不覆盖已有编号。调用方须传入同一层级的远端条目。"""
    if (
        not media_item
        or not remote
        or not _ids_compatible(media_item, remote)
        or not (_has_shared_provider_id(media_item, remote) or _titles_match(media_item, remote))
    ):
        return False
    before = (media_item.imdb_id, media_item.tmdb_id, media_item.tvdb_id)
    changed = fill_blank_external_ids(session, media_item, remote)
    if changed:
        logger.info(
            "    ✓ 补全编号 %s: IMDb %s→%s TMDB %s→%s TVDB %s→%s",
            media_item_label(media_item),
            before[0] or "-",
            media_item.imdb_id or "-",
            before[1] or "-",
            media_item.tmdb_id or "-",
            before[2] or "-",
            media_item.tvdb_id or "-",
        )
    return changed


def _incomplete_provider_ids(media_item: MediaItem) -> bool:
    return (
        is_blank(media_item.imdb_id)
        or is_blank(media_item.tmdb_id)
        or is_blank(media_item.tvdb_id)
    )


def _fill_series_ids_from_client(session, client: MediaServerClient, media_item: MediaItem):
    """按已有编号再查远端剧，补全父剧空着的 IMDb/TMDB/TVDB。"""
    if not media_item or not _incomplete_provider_ids(media_item):
        return
    items = query_by_providers(client, media_item, [ITEM_SERIES])
    matched = pick_remote_item(items, media_item, force_series=True)
    fill_blank_provider_ids(session, media_item, matched)


def _resolve_movie(session, item: RemoteItem, create=True):
    number_item = number_item_for_remote(session, item)
    if number_item:
        return number_item

    title = item.title or ""
    original_title = item.original_title or ""
    imdb_id, tmdb_id, tvdb_id = item.imdb_id, item.tmdb_id, item.tvdb_id

    media_item = find_by_provider_ids(session, "movie", imdb_id, tmdb_id, tvdb_id)
    if media_item:
        update_media_fields(
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

    filepath = item.path
    _record, extra = find_transfer_record(session, filepath)
    number = None
    if not (extra and extra.number) and filepath:
        number = get_number(filepath)
    if number and create:
        meta = metadata_for_number(session, number)
        if meta:
            media_item = ensure_number_media_item(session, number, meta.title or number)
            if media_item:
                fill_blank_external_ids(session, media_item, item)
                return media_item

    media_item = find_media_item_by_remote_id(session, item.remote_id, item.source)
    if media_item:
        return media_item

    if not create or not has_external_ids(imdb_id, tmdb_id, tvdb_id):
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


def _resolve_episode(session, item: RemoteItem, client: MediaServerClient, create=True):
    record, _extra = find_transfer_record(session, item.path)
    season = item.season
    episode_no = item.episode
    if record:
        if season < 0 and record.season is not None:
            season = record.season
        if episode_no < 0 and record.episode is not None:
            episode_no = record.episode

    if season < 0 or episode_no < 0:
        logger.debug(f"    ⊘ 缺少季/集编号，跳过: {item.path}")
        return None

    series = ensure_series(session, item, record, client, create)
    if not series:
        logger.debug(f"    ⊘ 无法解析剧集父项，跳过: {item.path or item.title}")
        return None
    imdb_id, tmdb_id, tvdb_id = item.imdb_id, item.tmdb_id, item.tvdb_id
    episode_title = item.title or ""
    series_name = (item.series_name or "").strip()
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
            update_media_fields(
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

    media_item = find_by_provider_ids(
        session, "episode", imdb_id, tmdb_id, tvdb_id, season, episode_no
    )
    if media_item:
        update_media_fields(
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


def _series_details_from_remote(item: RemoteItem, client: MediaServerClient):
    """只取剧级别编号。单集 IMDb/TMDB/TVDB 不能写到父剧上。"""
    if item.item_type == ITEM_SERIES:
        imdb_id, tmdb_id, tvdb_id = item.imdb_id, item.tmdb_id, item.tvdb_id
        original_title = item.original_title or ""
        series_name = (item.title or item.series_name or "").strip()
        if is_blank(imdb_id) or is_blank(tmdb_id) or is_blank(tvdb_id) or not original_title:
            details = client.get_item(item.remote_id)
            if details:
                imdb_id = imdb_id or details.imdb_id
                tmdb_id = tmdb_id or details.tmdb_id
                tvdb_id = tvdb_id or details.tvdb_id
                original_title = original_title or details.original_title or ""
                series_name = (details.title or series_name).strip()
        return imdb_id, tmdb_id, tvdb_id, original_title, series_name

    series_name = (item.series_name or "").strip()
    imdb_id = tmdb_id = tvdb_id = original_title = ""
    if item.series_remote_id:
        details = client.get_item(item.series_remote_id)
        if details:
            imdb_id, tmdb_id, tvdb_id = details.imdb_id, details.tmdb_id, details.tvdb_id
            original_title = details.original_title or ""
            series_name = (details.title or series_name).strip()
    if not series_name:
        series_name = (item.title or "").strip()
    return imdb_id, tmdb_id, tvdb_id, original_title, series_name


def ensure_series(session, item: RemoteItem, record, client: MediaServerClient, create=True):
    imdb_id, tmdb_id, tvdb_id, original_title, series_name = _series_details_from_remote(
        item, client
    )
    if not series_name and record and record.top_folder:
        series_name = record.top_folder.strip()

    media_item = None
    if has_external_ids(imdb_id, tmdb_id, tvdb_id):
        media_item = find_by_provider_ids(session, "tvshow", imdb_id, tmdb_id, tvdb_id)
    if not media_item and series_name:
        media_item = session.query(MediaItem).filter(
            MediaItem.media_type == "tvshow",
            MediaItem.title == series_name,
        ).first()
    if media_item:
        update_media_fields(
            session,
            media_item,
            media_type="tvshow",
            title=series_name or media_item.title,
            original_title=original_title or media_item.original_title,
            imdb_id=imdb_id or media_item.imdb_id,
            tmdb_id=tmdb_id or media_item.tmdb_id,
            tvdb_id=tvdb_id or media_item.tvdb_id,
        )
        if _incomplete_provider_ids(media_item):
            _fill_series_ids_from_client(session, client, media_item)
        if has_external_ids(media_item.imdb_id, media_item.tmdb_id, media_item.tvdb_id):
            return media_item
        logger.debug(f"    ⊘ 已有剧集缺少 IMDB/TMDB/TVDB，跳过: {series_name}")
        return None
    if not create or not series_name:
        return None
    if not has_external_ids(imdb_id, tmdb_id, tvdb_id):
        logger.debug(f"    ⊘ 电视剧缺少 IMDB/TMDB/TVDB，跳过: {series_name}")
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


def media_item_label(media_item: MediaItem) -> str:
    if not media_item:
        return ""
    return (media_item.number or media_item.title or "").strip() or str(media_item.id)


def dest_paths_for_media_item(session, media_item: MediaItem) -> list:
    if not media_item or not (media_item.number or "").strip():
        return []
    number = media_item.number.strip()
    rows = session.query(TransRecords.destpath).join(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
    ).filter(ExtraInfo.number == number).all()
    return list(dict.fromkeys(path for (path,) in rows if path))


def paths_match(remote_path: str, destpath: str) -> bool:
    left = (remote_path or "").replace("\\", "/").rstrip("/").lower()
    right = (destpath or "").replace("\\", "/").rstrip("/").lower()
    if not left or not right:
        return False
    if left == right:
        return True
    return left.endswith(right) or right.endswith(left)


def remote_file_paths(item: RemoteItem) -> list:
    paths = []
    seen = set()
    candidates = []
    if item.path:
        candidates.append(item.path)
    candidates.extend(item.source_paths or [])
    for path in candidates:
        key = (path or "").replace("\\", "/").rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def _like_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_record_for_path(session, remote_path: str):
    """一条远端路径对到一条记录。先全等，再按后缀比较。"""
    if not remote_path:
        return None
    record, _extra = find_transfer_record(session, remote_path)
    if record:
        return record
    basename = os.path.basename(remote_path.replace("\\", "/").rstrip("/"))
    if not basename:
        return None
    rows = (
        session.query(TransRecords)
        .filter(TransRecords.destpath.ilike(f"%{_like_escape(basename)}", escape="\\"))
        .all()
    )
    matches = [row for row in rows if paths_match(remote_path, row.destpath or "")]
    if not matches:
        return None
    norm = remote_path.replace("\\", "/").rstrip("/").lower()
    matches.sort(
        key=lambda row: (
            (row.destpath or "").replace("\\", "/").rstrip("/").lower() == norm,
            len(row.destpath or ""),
        ),
        reverse=True,
    )
    return matches[0]


def number_item_for_remote(session, item: RemoteItem):
    if item.item_type not in (ITEM_MOVIE, ITEM_VIDEO):
        return None
    for path in remote_file_paths(item):
        record = find_record_for_path(session, path)
        if not record:
            continue
        number_item = media_item_for_numbered_record(session, record, create=True)
        if number_item:
            return number_item
    return None


def link_remote_files(session, item: RemoteItem, media_item: MediaItem) -> None:
    """电影、视频、单集按路径写上 media_item_id。剧和季不绑。"""
    if not media_item or item.item_type not in (ITEM_MOVIE, ITEM_VIDEO, ITEM_EPISODE):
        return
    changed = False
    seen = set()
    for path in remote_file_paths(item):
        record = find_record_for_path(session, path)
        if not record or record.id in seen:
            continue
        seen.add(record.id)
        target = media_item
        if item.item_type in (ITEM_MOVIE, ITEM_VIDEO):
            number_item = media_item_for_numbered_record(session, record, create=True)
            if number_item:
                fill_blank_external_ids(session, number_item, item)
                target = number_item
        if record.media_item_id != target.id:
            record.media_item_id = target.id
            changed = True
    if changed or session.new or session.dirty:
        session.commit()


def find_remote_id_for_media_item(session, client: MediaServerClient, media_item: MediaItem) -> str:
    if media_item.media_type == "episode":
        return _find_episode_id(session, client, media_item)
    if media_item.media_type == UNLINKED_VIDEO_TYPE:
        row = session.query(CollectionItem).filter(
            CollectionItem.media_item_id == media_item.id,
            CollectionItem.external_item_id.isnot(None),
            CollectionItem.external_item_id != "",
        ).first()
        return row.external_item_id if row else None
    if (media_item.number or "").strip():
        return _find_id_by_destpath(session, client, media_item)

    include_types = [ITEM_SERIES] if media_item.media_type == "tvshow" else [ITEM_MOVIE, ITEM_VIDEO]
    items = query_by_providers(client, media_item, include_types)
    matched = pick_remote_item(items, media_item)
    if matched:
        fill_blank_provider_ids(session, media_item, matched)
        return matched.remote_id
    term = (media_item.title or "").strip()
    if term:
        items = client.query_items(include_types, search_term=term, limit=100)
        matched = pick_remote_item(items, media_item)
        if matched:
            fill_blank_provider_ids(session, media_item, matched)
            return matched.remote_id
    return None


def _version_file_suffixes() -> list:
    suffixes = []
    for version in ("leak", "hack", "uncensored"):
        suffix = version_suffix_for(version)
        if suffix and suffix not in suffixes:
            suffixes.append(suffix)
    suffixes.sort(key=len, reverse=True)
    return suffixes


def _stem_without_version_suffix(stem: str, number: str) -> str:
    """文件名把破解、流出写进番号（MIDD-791-U），NFO 标题里的番号没有这截。"""
    number = (number or "").strip()
    if not stem or not number:
        return ""
    for suffix in _version_file_suffixes():
        tagged = f"{number}{suffix}"
        if tagged in stem:
            return stem.replace(tagged, number, 1)
    return ""


def _destpath_search_terms(destpath: str, number: str) -> list:
    """Emby 的搜索看条目标题，不看文件路径。

    只拿带版本后缀的文件名去搜会对不上标题。目录名、去掉后缀后的标题、番号
    都可能出现在标题里，命中后再用路径确认是不是这一份文件。
    """
    normalized = (destpath or "").replace("\\", "/").rstrip("/")
    filename = os.path.basename(normalized)
    stem, _ext = os.path.splitext(filename)
    folder = os.path.basename(os.path.dirname(normalized))
    terms = []
    for term in (
        filename,
        stem,
        _stem_without_version_suffix(stem, number),
        folder,
        (number or "").strip(),
    ):
        cleaned = (term or "").strip()
        if cleaned and cleaned not in terms:
            terms.append(cleaned)
    return terms


def _item_matches_destpath(item: RemoteItem, destpath: str) -> bool:
    return any(paths_match(path, destpath) for path in remote_file_paths(item))


def _find_id_by_destpath(session, client: MediaServerClient, media_item: MediaItem) -> str:
    include_types = [ITEM_SERIES] if media_item.media_type == "tvshow" else [ITEM_MOVIE, ITEM_VIDEO]
    number = (media_item.number or "").strip()
    for destpath in dest_paths_for_media_item(session, media_item):
        for term in _destpath_search_terms(destpath, number):
            items = client.query_items(include_types, search_term=term, limit=50)
            for item in items:
                if _item_matches_destpath(item, destpath):
                    return item.remote_id
    return None


def _find_episode_id(session, client: MediaServerClient, media_item: MediaItem) -> str:
    items = query_by_providers(client, media_item, [ITEM_EPISODE])
    matched = pick_remote_item(items, media_item)
    if matched:
        fill_blank_provider_ids(session, media_item, matched)
        return matched.remote_id
    series = None
    if media_item.series_id:
        series = session.query(MediaItem).filter(MediaItem.id == media_item.series_id).first()
    series_remote_id = None
    if series:
        series_remote_id = find_remote_id_for_media_item(session, client, series)
    if not series_remote_id and (media_item.original_title or "").strip():
        series_items = client.query_items(
            [ITEM_SERIES], search_term=media_item.original_title.strip()
        )
        series_match = pick_remote_item(series_items, series or media_item, force_series=True)
        if series_match:
            if series:
                fill_blank_provider_ids(session, series, series_match)
            series_remote_id = series_match.remote_id
    if series_remote_id:
        episodes = client.query_items([ITEM_EPISODE], parent_id=series_remote_id, limit=500)
        matched = pick_remote_item(episodes, media_item)
        if matched:
            fill_blank_provider_ids(session, media_item, matched)
            return matched.remote_id
    return None


def query_by_providers(client: MediaServerClient, media_item: MediaItem, item_types: list):
    items = []
    seen = set()
    lookups = []
    if media_item.imdb_id:
        lookups.append({"imdb_id": media_item.imdb_id})
    if media_item.tmdb_id:
        lookups.append({"tmdb_id": media_item.tmdb_id})
    if media_item.tvdb_id:
        lookups.append({"tvdb_id": media_item.tvdb_id})
    for kwargs in lookups:
        for item in client.query_items(item_types, **kwargs):
            if item.remote_id and item.remote_id not in seen:
                seen.add(item.remote_id)
                items.append(item)
    return items


def pick_remote_item(items, media_item: MediaItem, force_series=False):
    if not items:
        return None
    if force_series or media_item.media_type == "tvshow":
        typed = [item for item in items if item.item_type == ITEM_SERIES]
        items = typed or items
        title = ((media_item.title if media_item.media_type == "tvshow" else media_item.original_title)
                 or media_item.title or "").strip().lower()
        if title:
            for item in items:
                if (item.title or "").strip().lower() == title:
                    return item
        return items[0]
    if media_item.media_type == "episode":
        season = media_item.season_number
        episode_no = media_item.episode_number
        for item in items:
            if item.item_type not in (ITEM_EPISODE,):
                continue
            if item.season == season and item.episode == episode_no:
                return item
        return None
    number = (media_item.number or "").strip().lower()
    number_compact = number.replace("-", "").replace("_", "")
    if number:
        for item in items:
            name = (item.title or "").strip().lower()
            path = (item.path or "").replace("\\", "/").lower()
            if number in name or number in path:
                return item
            if number_compact and (
                number_compact in name.replace("-", "").replace("_", "")
                or number_compact in path.replace("-", "").replace("_", "")
            ):
                return item
        return None
    title = (media_item.title or "").strip().lower()
    if title:
        for item in items:
            if (item.title or "").strip().lower() == title:
                return item
    movies = [item for item in items if item.item_type in (ITEM_MOVIE, ITEM_VIDEO)]
    return (movies or items)[0]
