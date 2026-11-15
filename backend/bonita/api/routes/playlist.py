from typing import Any, List, Literal

from fastapi import APIRouter, HTTPException, Query
import logging

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.playlist_service import PlaylistService

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_public(playlist) -> schemas.PlaylistPublic:
    return schemas.PlaylistPublic.model_validate(playlist)


def _require_playlist(service: PlaylistService, playlist_id: int):
    playlist = service.get_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="播放列表不存在")
    return playlist


@router.get("/plex", response_model=List[schemas.PlexPlaylistCandidate])
async def search_plex_playlists(
    session: SessionDep,
    search: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """从 Plex 搜索普通 audio 播放列表，不入库。已加入白名单的会标记 added。"""
    try:
        return PlaylistService(session).search_remote_playlists(search=search, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=schemas.PlaylistCollection)
async def list_playlists(session: SessionDep) -> Any:
    rows = PlaylistService(session).list_playlists()
    return schemas.PlaylistCollection(data=[_to_public(row) for row in rows], count=len(rows))


@router.post("/", response_model=schemas.PlaylistPublic)
async def add_playlist(session: SessionDep, payload: schemas.PlaylistCreate) -> Any:
    """加入白名单并立即从 Plex 拉取成员。"""
    if not (payload.external_id or "").strip() and not (payload.rating_key or "").strip():
        raise HTTPException(status_code=400, detail="缺少 external_id")
    try:
        playlist = PlaylistService(session).add_playlist(
            (payload.external_id or "").strip(),
            name=payload.name,
            rating_key=(payload.rating_key or "").strip() or None,
            source=payload.source,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_public(playlist)


@router.post("/sync", response_model=schemas.TaskStatus)
async def sync_all_playlists(
    session: SessionDep,
    direction: Literal["from_server", "to_server"] = Query(default="from_server"),
) -> Any:
    try:
        return PlaylistService(session).enqueue_sync(None, direction=direction)
    except Exception as e:
        logger.exception("播放列表批量同步入队失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{playlist_id}/sync", response_model=schemas.TaskStatus)
async def sync_one_playlist(
    playlist_id: int,
    session: SessionDep,
    direction: Literal["from_server", "to_server"] = Query(default="from_server"),
) -> Any:
    service = PlaylistService(session)
    _require_playlist(service, playlist_id)
    try:
        return service.enqueue_sync(playlist_id, direction=direction)
    except Exception as e:
        logger.exception(f"播放列表同步入队失败 {playlist_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{playlist_id}", response_model=schemas.PlaylistDetail)
async def get_playlist(playlist_id: int, session: SessionDep) -> Any:
    service = PlaylistService(session)
    playlist = _require_playlist(service, playlist_id)
    playlist, items = service.get_detail(playlist)
    detail = schemas.PlaylistDetail.model_validate(playlist)
    detail.items = [schemas.PlaylistItemPublic.model_validate(row) for row in items]
    return detail


@router.delete("/{playlist_id}", response_model=schemas.Response)
async def remove_playlist(playlist_id: int, session: SessionDep) -> Any:
    service = PlaylistService(session)
    playlist = _require_playlist(service, playlist_id)
    service.delete_playlist(playlist)
    return schemas.Response(success=True, message="已从同步列表移除")

