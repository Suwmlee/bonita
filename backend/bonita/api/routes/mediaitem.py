from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from bonita.api.deps import SessionDep
from bonita.db.models.mediaitem import MediaItem
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
    - favorite: True只返回已喜爱的内容，False只返回未喜爱的内容，None返回所有内容
    """
    # 创建包含观看信息的子查询
    watch_info = (
        session.query(
            WatchHistory.media_item_id,
            func.max(WatchHistory.watched).label("watched"),
            func.max(WatchHistory.favorite).label("favorite"),
            func.sum(WatchHistory.watch_count).label("total_plays"),
            func.max(WatchHistory.play_progress).label("play_progress"),
            func.max(WatchHistory.duration).label("duration"),
            func.max(WatchHistory.has_rating).label("has_rating"),
            func.max(WatchHistory.rating).label("rating"),
            func.max(WatchHistory.updatetime).label("watch_updatetime"),
        )
        .group_by(WatchHistory.media_item_id)
        .subquery()
    )

    # 主查询
    query = (
        session.query(
            MediaItem,
            watch_info.c.favorite,
            watch_info.c.watched,
            watch_info.c.total_plays,
            watch_info.c.play_progress,
            watch_info.c.duration,
            watch_info.c.has_rating,
            watch_info.c.rating,
            watch_info.c.watch_updatetime
        )
        .outerjoin(watch_info, MediaItem.id == watch_info.c.media_item_id)
    )

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

    # 按番号状态过滤
    if has_number is not None:
        if has_number:
            query = query.filter(MediaItem.number.isnot(None), MediaItem.number != '')
        else:
            query = query.filter((MediaItem.number.is_(None)) | (MediaItem.number == ''))

    # 按观看状态过滤
    if watched is not None:
        if watched:
            query = query.filter(watch_info.c.watched > 0)
        else:
            query = query.filter((watch_info.c.watched == 0) | (watch_info.c.watched.is_(None)))

    # 按喜爱状态过滤
    if favorite is not None:
        if favorite:
            query = query.filter(watch_info.c.favorite > 0)
        else:
            query = query.filter((watch_info.c.favorite == 0) | (watch_info.c.favorite.is_(None)))

    # 获取总数
    count = query.count()

    # 应用排序
    sort_column = getattr(MediaItem, sort_by, MediaItem.updatetime)
    query = query.order_by(desc(sort_column) if sort_desc else asc(sort_column))

    # 分页
    results = query.offset(skip).limit(limit).all()

    # 构造结果
    items = []
    for media_item, favorite, watched, total_plays, play_progress, duration, has_rating, rating, watch_updatetime in results:
        item_dict = schemas.MediaItemInDB.model_validate(media_item)

        # 创建用户数据对象
        userdata = schemas.UserWatchData(
            favorite=favorite or False,
            watched=watched or False,
            total_plays=total_plays or 0,
            play_progress=play_progress,
            duration=duration,
            has_rating=has_rating or False,
            user_rating=rating,
            last_played=watch_updatetime,
            watch_updatetime=watch_updatetime
        )

        # 创建带有用户数据的媒体项
        item_with_watches = schemas.MediaItemWithWatches(
            **item_dict.model_dump(),
            userdata=userdata
        )

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
    同时删除关联的观看历史记录
    """
    media_item = session.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="媒体项不存在")

    watch_history_deleted = session.query(WatchHistory).filter(
        WatchHistory.media_item_id == media_id).delete(synchronize_session=False)
    session.delete(media_item)
    session.commit()

    return {
        "detail": "媒体项已删除",
        "watch_history_deleted": watch_history_deleted
    }


@router.post("/clean")
async def clean_media_item(
    session: SessionDep
) -> Any:
    """
    清理媒体项
    1. 删除番号重复的媒体项（保留最新的一条）
    """

    # 查找有重复番号的媒体项
    duplicate_numbers = (
        session.query(MediaItem.number)
        .filter(MediaItem.number.isnot(None), MediaItem.number != '')
        .group_by(MediaItem.number)
        .having(func.count(MediaItem.id) > 1)
        .all()
    )

    duplicate_count = 0
    watch_history_deleted = 0
    # 对每个重复的番号，保留最新的一条记录，删除其他记录
    for (number,) in duplicate_numbers:
        # 获取该番号的所有媒体项，按更新时间降序排序
        items = (
            session.query(MediaItem)
            .filter(MediaItem.number == number)
            .order_by(desc(MediaItem.updatetime))
            .all()
        )

        # 保留第一条（最新的），删除其余的
        for item in items[1:]:
            # 先删除关联的观看历史记录
            deleted_count = session.query(WatchHistory).filter(
                WatchHistory.media_item_id == item.id).delete(synchronize_session=False)
            watch_history_deleted += deleted_count

            # 然后删除媒体项
            session.delete(item)
            duplicate_count += 1

    session.commit()
    return {
        "detail": "媒体项已清理",
        "duplicate_number_deleted": duplicate_count,
        "watch_history_deleted": watch_history_deleted
    }
