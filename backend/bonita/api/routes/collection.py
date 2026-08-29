from typing import Any, List, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.api.routes.mediaitem import attach_watch_data
from bonita.db.models.collection import Collection, CollectionItem
from bonita.db.models.mediaitem import MediaItem
from bonita.modules.media_service.emby import EmbyService
from bonita.modules.media_service.sync import (
    add_and_sync_collection,
    add_collection_members,
    remove_collection_member,
    sync_collection_members,
    sync_whitelisted_collections,
    _refresh_collection_meta,
)

router = APIRouter()


def _to_public(collection: Collection) -> schemas.CollectionPublic:
    return schemas.CollectionPublic.model_validate(collection)


def _get_collection(session: SessionDep, collection_id: int) -> Collection:
    collection = session.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="合集不存在")
    return collection


@router.get("/emby", response_model=List[schemas.EmbyCollectionCandidate])
async def search_emby_collections(
    session: SessionDep,
    search: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """从 Emby 搜索合集，不入库。已加入白名单的会标记 added。"""
    emby_service = EmbyService()
    if not emby_service.is_initialized:
        raise HTTPException(status_code=400, detail="Emby服务未初始化")
    items = emby_service.search_boxsets(search.strip(), limit=limit)
    added_ids = {
        row.emby_id for row in session.query(Collection.emby_id).all()
    }
    results = []
    for item in items:
        emby_id = item.get("Id")
        if not emby_id:
            continue
        child_count = item.get("ChildCount")
        if child_count is None:
            child_count = item.get("RecursiveItemCount") or 0
        results.append(
            schemas.EmbyCollectionCandidate(
                emby_id=emby_id,
                name=item.get("Name") or "",
                child_count=int(child_count or 0),
                image_tag=(item.get("ImageTags") or {}).get("Primary"),
                added=emby_id in added_ids,
            )
        )
    return results


@router.get("/", response_model=schemas.CollectionCollection)
async def list_collections(session: SessionDep) -> Any:
    rows = session.query(Collection).order_by(Collection.updatetime.desc()).all()
    for row in rows:
        if not row.name or row.name == row.emby_id:
            try:
                _refresh_collection_meta(session, row)
            except Exception:
                pass
    return schemas.CollectionCollection(data=[_to_public(row) for row in rows], count=len(rows))


@router.post("/", response_model=schemas.CollectionPublic)
async def add_collection(session: SessionDep, payload: schemas.CollectionCreate) -> Any:
    """加入白名单并立即从 Emby 拉取成员。"""
    try:
        collection = add_and_sync_collection(session, payload.emby_id, payload.name)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_public(collection)


@router.post("/sync", response_model=schemas.Response)
async def sync_all_collections(
    session: SessionDep,
    direction: Literal["from_emby", "to_emby"] = Query(default="from_emby"),
) -> Any:
    try:
        synced = sync_whitelisted_collections(session, direction=direction)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    message = (
        f"已从 Emby 拉取 {synced} 个合集"
        if direction == "from_emby"
        else f"已回写 {synced} 个合集到 Emby"
    )
    return schemas.Response(success=True, message=message, data={"synced": synced})


@router.post("/{collection_id}/sync", response_model=schemas.CollectionPublic)
async def sync_one_collection(
    collection_id: int,
    session: SessionDep,
    direction: Literal["from_emby", "to_emby"] = Query(default="from_emby"),
) -> Any:
    collection = _get_collection(session, collection_id)
    try:
        collection = sync_collection_members(session, collection, direction=direction)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_public(collection)


@router.get("/{collection_id}/candidates", response_model=List[schemas.MediaItemWithWatches])
async def search_collection_candidates(
    collection_id: int,
    session: SessionDep,
    search: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
) -> Any:
    """搜索尚未加入该合集的本地媒体项。"""
    _get_collection(session, collection_id)
    member_ids = [
        row[0]
        for row in session.query(CollectionItem.media_item_id).filter(
            CollectionItem.collection_id == collection_id
        ).all()
    ]
    query = session.query(MediaItem)
    if member_ids:
        query = query.filter(~MediaItem.id.in_(member_ids))
    query = query.filter(
        ~((MediaItem.media_type == "episode") & (
            (MediaItem.season_number < 0) | (MediaItem.episode_number < 0)
        ))
    )
    keyword = search.strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                MediaItem.title.ilike(like),
                MediaItem.original_title.ilike(like),
                MediaItem.number.ilike(like),
            )
        )
    media_items = query.order_by(MediaItem.updatetime.desc()).limit(limit).all()
    return attach_watch_data(session, media_items)


@router.post("/{collection_id}/items", response_model=schemas.CollectionPublic)
async def add_items_to_collection(
    collection_id: int,
    payload: schemas.CollectionAddItems,
    session: SessionDep,
) -> Any:
    collection = _get_collection(session, collection_id)
    add_collection_members(session, collection, payload.media_item_ids)
    return _to_public(collection)


@router.delete("/{collection_id}/items/{media_item_id}", response_model=schemas.CollectionPublic)
async def remove_item_from_collection(
    collection_id: int,
    media_item_id: int,
    session: SessionDep,
) -> Any:
    collection = _get_collection(session, collection_id)
    if not remove_collection_member(session, collection, media_item_id):
        raise HTTPException(status_code=404, detail="合集中没有该媒体项")
    return _to_public(collection)


@router.get("/{collection_id}", response_model=schemas.CollectionDetail)
async def get_collection(collection_id: int, session: SessionDep) -> Any:
    collection = _get_collection(session, collection_id)
    if not collection.name or collection.name == collection.emby_id:
        try:
            _refresh_collection_meta(session, collection)
        except Exception:
            pass
    media_items = (
        session.query(MediaItem)
        .join(CollectionItem, CollectionItem.media_item_id == MediaItem.id)
        .filter(CollectionItem.collection_id == collection_id)
        .order_by(MediaItem.title.asc())
        .all()
    )
    detail = schemas.CollectionDetail.model_validate(collection)
    detail.items = attach_watch_data(session, media_items)
    return detail


@router.delete("/{collection_id}", response_model=schemas.Response)
async def remove_collection(collection_id: int, session: SessionDep) -> Any:
    collection = _get_collection(session, collection_id)
    session.delete(collection)
    session.commit()
    return schemas.Response(success=True, message="已从同步列表移除")
