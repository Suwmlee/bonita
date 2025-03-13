from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from bonita.api.deps import SessionDep
from bonita.db.models.media_item import MediaItem
from bonita.db.models.watch_history import WatchHistory
from bonita import schemas

router = APIRouter()


@router.get("/", response_model=schemas.MediaItemCollection)
async def get_media_items(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    media_type: str = None,
    sort_by: str = "title",
    sort_desc: bool = False
) -> Any:
    """
    获取媒体项列表
    支持按标题搜索、类型过滤和排序
    """
    query = session.query(MediaItem)
    
    # 应用搜索过滤
    if search:
        query = query.filter(
            MediaItem.title.ilike(f"%{search}%") |
            MediaItem.original_title.ilike(f"%{search}%") |
            MediaItem.number.ilike(f"%{search}%")
        )
    
    # 按媒体类型过滤
    if media_type:
        query = query.filter(MediaItem.media_type == media_type)
    
    # 获取总数
    count = query.count()
    
    # 应用排序
    sort_column = getattr(MediaItem, sort_by, MediaItem.title)
    query = query.order_by(desc(sort_column) if sort_desc else asc(sort_column))
    
    # 分页
    items = query.offset(skip).limit(limit).all()
    
    return schemas.MediaItemCollection(data=items, count=count)


@router.get("/watches", response_model=schemas.MediaItemCollection)
async def get_watched_media_items(
    session: SessionDep,
    skip: int = 0, 
    limit: int = 100,
    source: str = None,
    sort_by: str = "last_played",
    sort_desc: bool = True
) -> Any:
    """
    获取已观看的媒体项列表
    按最后观看时间排序
    """
    # 创建包含观看信息的子查询
    watch_info = (
        session.query(
            WatchHistory.media_item_id,
            func.count(WatchHistory.id).label("total_plays"),
            func.max(WatchHistory.played_at).label("last_played"),
            func.avg(WatchHistory.rating).label("user_rating")
        )
    )
    
    # 应用来源过滤
    if source:
        watch_info = watch_info.filter(WatchHistory.source == source)
    
    # 分组聚合
    watch_info = watch_info.group_by(WatchHistory.media_item_id).subquery()
    
    # 主查询
    query = (
        session.query(
            MediaItem,
            watch_info.c.total_plays,
            watch_info.c.last_played,
            watch_info.c.user_rating
        )
        .join(watch_info, MediaItem.id == watch_info.c.media_item_id)
    )
    
    # 获取总数
    count = query.count()
    
    # 应用排序
    if sort_by == "last_played":
        query = query.order_by(desc(watch_info.c.last_played) if sort_desc else asc(watch_info.c.last_played))
    elif sort_by == "total_plays":
        query = query.order_by(desc(watch_info.c.total_plays) if sort_desc else asc(watch_info.c.total_plays))
    elif sort_by == "user_rating":
        query = query.order_by(desc(watch_info.c.user_rating) if sort_desc else asc(watch_info.c.user_rating))
    else:
        sort_column = getattr(MediaItem, sort_by, MediaItem.title)
        query = query.order_by(desc(sort_column) if sort_desc else asc(sort_column))
    
    # 分页
    results = query.offset(skip).limit(limit).all()
    
    # 构造结果
    items = []
    for media_item, total_plays, last_played, user_rating in results:
        item_dict = schemas.MediaItemInDB.model_validate(media_item)
        item_with_watches = schemas.MediaItemWithWatches(**{
            **item_dict.model_dump(),
            "total_plays": total_plays or 0,
            "last_played": last_played,
            "user_rating": user_rating
        })
        items.append(item_with_watches)
    
    return schemas.MediaItemCollection(data=items, count=count)


@router.get("/{media_id}", response_model=schemas.MediaItemInDB)
async def get_media_item(
    media_id: int,
    session: SessionDep
) -> Any:
    """
    获取单个媒体项详情
    """
    media_item = session.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="媒体项不存在")
    return media_item


@router.post("/", response_model=schemas.MediaItemInDB)
async def create_media_item(
    media_item_in: schemas.MediaItemCreate,
    session: SessionDep
) -> Any:
    """
    创建新的媒体项
    """
    media_item = MediaItem(**media_item_in.model_dump())
    session.add(media_item)
    session.commit()
    session.refresh(media_item)
    return media_item


@router.put("/{media_id}", response_model=schemas.MediaItemInDB)
async def update_media_item(
    media_id: int,
    media_item_in: schemas.MediaItemUpdate,
    session: SessionDep
) -> Any:
    """
    更新媒体项
    """
    media_item = session.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="媒体项不存在")
    
    update_data = media_item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(media_item, field, value)
        
    session.add(media_item)
    session.commit()
    session.refresh(media_item)
    return media_item


@router.delete("/{media_id}")
async def delete_media_item(
    media_id: int,
    session: SessionDep
) -> Any:
    """
    删除媒体项
    """
    media_item = session.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="媒体项不存在")
    
    session.delete(media_item)
    session.commit()
    return {"detail": "媒体项已删除"} 