from typing import Any
from fastapi import APIRouter, HTTPException

from bonita.api.deps import SessionDep
from bonita.services.mediaitem_service import MediaItemService
from bonita import schemas

router = APIRouter()


@router.get("/", response_model=schemas.MediaItemCollection)
async def get_media_items(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    media_type: str = None,
    sort_by: str = "updatetime",
    sort_desc: bool = True,
    has_number: bool = None,
    watched: bool = None,
    favorite: bool = None
) -> Any:
    """
    获取媒体项列表
    支持按标题搜索、类型过滤和排序
    - has_number: True只返回有番号的内容，False只返回没有番号的内容，None返回所有内容
    - watched: True只返回已观看的内容，False只返回未观看的内容，None返回所有内容
    - favorite: True只返回已收藏的内容，False只返回未收藏的内容，None返回所有内容
    """
    items, count = MediaItemService(session).list_media_items(
        skip=skip,
        limit=limit,
        search=search,
        media_type=media_type,
        sort_by=sort_by,
        sort_desc=sort_desc,
        has_number=has_number,
        watched=watched,
        favorite=favorite,
    )
    return schemas.MediaItemCollection(data=items, count=count)


@router.get("/{media_id}", response_model=schemas.MediaItemWithWatches)
async def get_media_item(
    media_id: int,
    session: SessionDep
) -> Any:
    """
    获取单个媒体项详情
    包含观看历史信息
    """
    item = MediaItemService(session).get_with_watch_data(media_id)
    if not item:
        raise HTTPException(status_code=404, detail="媒体项不存在")
    return item


@router.post("/", response_model=schemas.MediaItemInDB)
async def create_media_item(
    media_item_in: schemas.MediaItemCreate,
    session: SessionDep
) -> Any:
    """
    创建新的媒体项
    """
    return MediaItemService(session).create_media_item(media_item_in.model_dump())


@router.put("/{media_id}", response_model=schemas.MediaItemWithWatches)
async def update_media_item(
    media_id: int,
    media_item_in: schemas.MediaItemUpdate,
    session: SessionDep
) -> Any:
    """
    更新媒体项
    支持更新媒体项基础信息和观看历史信息
    """
    item = MediaItemService(session).update_media_item(
        media_id, media_item_in.model_dump(exclude_unset=True)
    )
    if not item:
        raise HTTPException(status_code=404, detail="媒体项不存在")
    return item


@router.delete("/{media_id}")
async def delete_media_item(
    media_id: int,
    session: SessionDep
) -> Any:
    """
    删除媒体项
    同时删除关联的观看历史记录
    """
    result = MediaItemService(session).delete_media_item(media_id)
    if not result:
        raise HTTPException(status_code=404, detail="媒体项不存在")
    return result


@router.post("/clean")
async def clean_media_item(
    session: SessionDep
) -> Any:
    """
    清理媒体项
    1. 删除番号重复的媒体项（保留最新的一条）
    """
    return MediaItemService(session).clean_duplicate_numbers()
