import logging
from datetime import datetime

from bonita.db.models.playlist import Playlist, PlaylistItem
from bonita.modules.media_service.client import (
    SOURCE_PLEX,
    is_to_server,
    source_label,
)
from bonita.modules.media_service.factory import require_plex_client
from bonita.modules.media_service.matching import paths_match

logger = logging.getLogger(__name__)

MIRROR_SUFFIX = " · 同步"


def mirror_playlist_title(name: str) -> str:
    base = (name or "").strip() or "Playlist"
    return base if base.endswith(MIRROR_SUFFIX) else f"{base}{MIRROR_SUFFIX}"


def _apply_ref(session, playlist: Playlist, details, fallback_name: str = None) -> None:
    """用远端 PlaylistRef 刷新本地元数据（不 commit）。"""
    if details.rating_key:
        playlist.rating_key = details.rating_key
    playlist.is_smart = bool(details.smart)
    if details.remote_id and playlist.external_id != details.remote_id:
        clash = (
            session.query(Playlist.id)
            .filter(
                Playlist.source == (playlist.source or SOURCE_PLEX),
                Playlist.external_id == details.remote_id,
                Playlist.id != playlist.id,
            )
            .first()
        )
        if not clash:
            playlist.external_id = details.remote_id
    name = (
        (details.name or "").strip()
        or (fallback_name or "").strip()
        or playlist.name
        or playlist.external_id
    )
    if name:
        playlist.name = name
    if details.leaf_count:
        playlist.item_count = details.leaf_count


def _locate_playlist(client, playlist: Playlist):
    """定位远端列表并返回 (rating_key, PlaylistRef|None)。"""
    if playlist.rating_key:
        details = client.get_playlist(playlist.rating_key)
        if details and (
            not playlist.external_id or details.remote_id == playlist.external_id
        ):
            return details.rating_key, details
    if playlist.external_id:
        for ref in client.list_audio_playlists(limit=500, include_smart=True):
            if ref.remote_id == playlist.external_id or ref.guid == playlist.external_id:
                return ref.rating_key, ref
    return playlist.rating_key or "", None


def refresh_playlist_meta(session, playlist: Playlist, fallback_name: str = None):
    from bonita.modules.media_service.factory import get_plex_client

    client = get_plex_client()
    if not client:
        return
    rating_key, details = _locate_playlist(client, playlist)
    if not details and rating_key:
        details = client.get_playlist(rating_key)
    if not details:
        return
    _apply_ref(session, playlist, details, fallback_name=fallback_name)
    session.commit()


def add_and_sync_playlist(
    session,
    external_id: str,
    name: str = None,
    rating_key: str = None,
    source: str = SOURCE_PLEX,
) -> Playlist:
    client = require_plex_client()
    external_id = (external_id or "").strip()
    rating_key = (rating_key or "").strip() or None
    details = client.get_playlist(rating_key) if rating_key else None
    if details:
        external_id = external_id or details.remote_id
        name = name or details.name
        rating_key = details.rating_key
    if not external_id:
        raise RuntimeError("缺少播放列表 external_id")

    playlist = (
        session.query(Playlist)
        .filter(Playlist.source == source, Playlist.external_id == external_id)
        .first()
    )
    if not playlist:
        playlist = Playlist(
            source=source,
            external_id=external_id,
            rating_key=rating_key,
            name=(name or "").strip() or external_id,
            is_smart=bool(details.smart) if details else False,
        )
        playlist.create(session)
    else:
        if rating_key:
            playlist.rating_key = rating_key
        if name and name.strip() and playlist.name in ("", playlist.external_id):
            playlist.name = name.strip()
        if details:
            playlist.is_smart = bool(details.smart)
        session.commit()

    if details:
        _apply_ref(session, playlist, details, fallback_name=name)
        session.commit()
    else:
        refresh_playlist_meta(session, playlist, fallback_name=name)
    return sync_playlist_from_server(session, playlist)


def sync_playlist_members(session, playlist: Playlist, direction: str = "from_server") -> Playlist:
    if is_to_server(direction):
        return sync_playlist_to_server(session, playlist)
    return sync_playlist_from_server(session, playlist)


def _require_located(client, session, playlist: Playlist):
    label = source_label(playlist.source or SOURCE_PLEX)
    rating_key, details = _locate_playlist(client, playlist)
    if details:
        _apply_ref(session, playlist, details)
    elif rating_key:
        details = client.get_playlist(rating_key)
        if details:
            _apply_ref(session, playlist, details)
            rating_key = details.rating_key
    if not rating_key:
        raise RuntimeError(f"无法在 {label} 定位播放列表: {playlist.name}")
    return rating_key, label


def sync_playlist_from_server(session, playlist: Playlist) -> Playlist:
    client = require_plex_client()
    rating_key, label = _require_located(client, session, playlist)
    logger.info(f"  → 播放列表 {playlist.name}: 从 {label} 拉取成员")

    tracks = client.get_playlist_items(rating_key)
    session.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist.id).delete(
        synchronize_session=False
    )
    session.flush()
    for track in tracks:
        session.add(
            PlaylistItem(
                playlist_id=playlist.id,
                media_item_id=None,
                external_item_id=track.rating_key,
                external_guid=track.guid or None,
                playlist_item_id=track.playlist_item_id,
                path=track.path,
                title=track.title or None,
                artist=track.artist or None,
                album=track.album or None,
                sort_index=track.sort_index,
            )
        )
    playlist.item_count = len(tracks)
    playlist.matched_count = len(tracks)
    playlist.last_sync_at = datetime.now()
    session.commit()
    session.refresh(playlist)
    logger.info(f"    ✓ 播放列表 {playlist.name}: 从 {label} 拉取 {len(tracks)} 项")
    return playlist


def _best_path_match(path: str, candidates):
    """candidates: iterable of (path, payload)。返回 payload。"""
    if not path:
        return None
    norm = path.replace("\\", "/").rstrip("/").lower()
    matches = [(p, payload) for p, payload in candidates if p and paths_match(path, p)]
    if not matches:
        return None
    matches.sort(
        key=lambda row: (
            (row[0] or "").replace("\\", "/").rstrip("/").lower() == norm,
            len(row[0] or ""),
        ),
        reverse=True,
    )
    return matches[0][1]


def _resolve_track_rating_key(client, member: PlaylistItem, hint_tracks, path_index_holder: list) -> str:
    """路径优先：hint 列表 → 音乐库索引 → 仍在 hint 中的缓存 ratingKey。"""
    cached = (member.external_item_id or "").strip()
    if member.path:
        hit = _best_path_match(member.path, ((t.path, t.rating_key) for t in hint_tracks))
        if hit:
            return hit
        if not path_index_holder:
            path_index_holder.append(client.build_music_track_path_index())
        looked_up = _best_path_match(member.path, path_index_holder[0])
        if looked_up:
            return looked_up
    hint_keys = {t.rating_key for t in hint_tracks if t.rating_key}
    if cached and cached in hint_keys:
        return cached
    return ""


def _track_label(member: PlaylistItem) -> str:
    title = (member.title or "").strip()
    artist = (member.artist or "").strip()
    if title and artist:
        return f"{artist} - {title}"
    return title or artist or member.path or member.external_item_id or str(member.id)


def _ensure_write_rating_key(client, playlist: Playlist, track_keys: list) -> str:
    if not playlist.is_smart:
        key = (playlist.rating_key or "").strip()
        if not key:
            raise RuntimeError(f"播放列表缺少 ratingKey: {playlist.name}")
        return key

    cached = (playlist.write_rating_key or "").strip()
    if cached:
        details = client.get_playlist(cached)
        if details and not details.smart:
            return details.rating_key
        playlist.write_rating_key = None

    title = mirror_playlist_title(playlist.name)
    for ref in client.list_audio_playlists(search=title, limit=100, include_smart=False):
        if ref.name == title and not ref.smart:
            playlist.write_rating_key = ref.rating_key
            return ref.rating_key

    if not track_keys:
        raise RuntimeError(
            f"智能列表「{playlist.name}」回写需要至少一首已解析曲目，才能创建「{title}」"
        )
    created = client.create_audio_playlist(title, track_keys)
    playlist.write_rating_key = created.rating_key
    logger.info(f"    ✓ 已创建回写目标 {title} ({created.rating_key})")
    return created.rating_key


def sync_playlist_to_server(session, playlist: Playlist) -> Playlist:
    client = require_plex_client()
    source_key, label = _require_located(client, session, playlist)
    target = mirror_playlist_title(playlist.name) if playlist.is_smart else playlist.name
    logger.info(f"  → 播放列表 {playlist.name}: 回写 {label} → {target}")

    members = (
        session.query(PlaylistItem)
        .filter(PlaylistItem.playlist_id == playlist.id)
        .order_by(PlaylistItem.sort_index.asc(), PlaylistItem.id.asc())
        .all()
    )
    hint_tracks = client.get_playlist_items(source_key)
    path_index_holder: list = []
    wanted_ids, seen = [], set()
    unresolved = 0
    for member in members:
        resolved = _resolve_track_rating_key(
            client, member, hint_tracks, path_index_holder
        )
        if not resolved:
            unresolved += 1
            logger.warning(
                f"    ⊘ {playlist.name}: 无法按路径找到 {_track_label(member)}"
            )
            continue
        member.external_item_id = resolved
        if resolved not in seen:
            wanted_ids.append(resolved)
            seen.add(resolved)

    write_key = _ensure_write_rating_key(client, playlist, wanted_ids)
    remote_tracks = client.get_playlist_items(write_key)
    remote_ids = {t.rating_key for t in remote_tracks if t.rating_key}
    wanted_set = set(wanted_ids)
    to_add = [k for k in wanted_ids if k not in remote_ids]
    to_remove_pids = [
        t.playlist_item_id
        for t in remote_tracks
        if t.rating_key in remote_ids - wanted_set and t.playlist_item_id
    ]

    added_ok = add_failed = removed_ok = remove_failed = 0
    if to_add:
        added_ok, add_failed = client.add_items_to_playlist(write_key, to_add)
    if to_remove_pids:
        removed_ok, remove_failed = client.remove_items_from_playlist(
            write_key, to_remove_pids
        )

    refreshed = {t.rating_key: t for t in client.get_playlist_items(write_key) if t.rating_key}
    for member in members:
        remote = refreshed.get((member.external_item_id or "").strip())
        if not remote:
            continue
        member.playlist_item_id = remote.playlist_item_id
        if remote.guid:
            member.external_guid = remote.guid
        if remote.path:
            member.path = remote.path

    if not playlist.is_smart:
        playlist.item_count = len(refreshed)
    playlist.matched_count = len(wanted_ids)
    playlist.last_sync_at = datetime.now()
    session.commit()
    session.refresh(playlist)
    extra = ""
    if add_failed:
        extra += f", 新增失败 {add_failed}"
    if remove_failed:
        extra += f", 移除失败 {remove_failed}"
    logger.info(
        f"    ✓ {playlist.name}: 回写新增 {added_ok}, 移除 {removed_ok}, "
        f"未对上 {unresolved}{extra}"
    )
    return playlist


def sync_whitelisted_playlists(session, direction: str = "from_server") -> int:
    playlists = session.query(Playlist).all()
    if not playlists:
        logger.info("  ⊘ 没有要同步的播放列表")
        return 0
    synced = 0
    for playlist in playlists:
        try:
            sync_playlist_members(session, playlist, direction=direction)
            synced += 1
        except Exception as e:
            logger.error(f"  ✗ 播放列表同步失败 {playlist.name}: {e}")
    return synced
