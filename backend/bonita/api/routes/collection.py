from typing import Any, List, Literal

from fastapi import APIRouter, HTTPException, Query
import logging

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.collection_service import CollectionService

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_public(collection) -> schemas.CollectionPublic:
    return schemas.CollectionPublic.model_validate(collection)


def _require_collection(service: CollectionService, collection_id: int):
    collection = service.get_by_id(collection_id)
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
    try:
        return CollectionService(session).search_remote_collections(search=search, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=schemas.CollectionCollection)
async def list_collections(session: SessionDep) -> Any:
    rows = CollectionService(session).list_collections()
    return schemas.CollectionCollection(data=[_to_public(row) for row in rows], count=len(rows))


@router.post("/", response_model=schemas.CollectionPublic)
async def add_collection(session: SessionDep, payload: schemas.CollectionCreate) -> Any:
    """加入白名单并立即从媒体服务器拉取成员。"""
    if not (payload.external_id or "").strip():
        raise HTTPException(status_code=400, detail="缺少 external_id")
    try:
        collection = CollectionService(session).add_collection(
            payload.external_id.strip(), payload.name, source=payload.source
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_public(collection)


@router.post("/sync", response_model=schemas.Response)
async def sync_all_collections(
    session: SessionDep,
    direction: Literal["from_server", "to_server"] = Query(default="from_server"),
) -> Any:
    try:
        synced = CollectionService(session).sync_all(direction=direction)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("合集批量同步失败")
        raise HTTPException(status_code=500, detail=str(e))
    return schemas.Response(
        success=True,
        message=CollectionService.sync_message(direction, synced),
        data={"synced": synced},
    )


@router.post("/{collection_id}/sync", response_model=schemas.CollectionPublic)
async def sync_one_collection(
    collection_id: int,
    session: SessionDep,
    direction: Literal["from_server", "to_server"] = Query(default="from_server"),
) -> Any:
    service = CollectionService(session)
    collection = _require_collection(service, collection_id)
    try:
        collection = service.sync_one(collection, direction=direction)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"合集同步失败 {collection.name}")
        raise HTTPException(status_code=500, detail=str(e))
    return _to_public(collection)


@router.get("/{collection_id}/candidates", response_model=List[schemas.MediaItemWithWatches])
async def search_collection_candidates(
    collection_id: int,
    session: SessionDep,
    search: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
) -> Any:
    """搜索尚未加入该合集的本地媒体项。"""
    service = CollectionService(session)
    _require_collection(service, collection_id)
    return service.search_candidates(collection_id, search=search, limit=limit)


@router.post("/{collection_id}/items", response_model=schemas.CollectionPublic)
async def add_items_to_collection(
    collection_id: int,
    payload: schemas.CollectionAddItems,
    session: SessionDep,
) -> Any:
    service = CollectionService(session)
    collection = _require_collection(service, collection_id)
    collection = service.add_items(collection, payload.media_item_ids)
    return _to_public(collection)


@router.delete("/{collection_id}/items/{media_item_id}", response_model=schemas.CollectionPublic)
async def remove_item_from_collection(
    collection_id: int,
    media_item_id: int,
    session: SessionDep,
) -> Any:
    service = CollectionService(session)
    collection = _require_collection(service, collection_id)
    if not service.remove_item(collection, media_item_id):
        raise HTTPException(status_code=404, detail="合集中没有该媒体项")
    return _to_public(collection)


@router.get("/{collection_id}", response_model=schemas.CollectionDetail)
async def get_collection(collection_id: int, session: SessionDep) -> Any:
    service = CollectionService(session)
    collection = _require_collection(service, collection_id)
    collection, items = service.get_detail(collection)
    detail = schemas.CollectionDetail.model_validate(collection)
    detail.items = items
    return detail


@router.delete("/{collection_id}", response_model=schemas.Response)
async def remove_collection(collection_id: int, session: SessionDep) -> Any:
    service = CollectionService(session)
    collection = _require_collection(service, collection_id)
    service.delete_collection(collection)
    return schemas.Response(success=True, message="已从同步列表移除")
