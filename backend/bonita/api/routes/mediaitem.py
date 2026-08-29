from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from bonita.api.deps import SessionDep
from bonita.db.models.mediaitem import MediaItem
from bonita.db.models.watch_history import WatchHistory
from bonita.services.metadata_service import MetadataService
from bonita import schemas

router = APIRouter()


def _series_info_map(session: Session, media_items: List[MediaItem]) -> dict:
    series_ids = {
        item.series_id for item in media_items
        if item.media_type == "episode" and item.series_id
    }
    if not series_ids:
        return {}
    series_rows = session.query(MediaItem).filter(MediaItem.id.in_(series_ids)).all()
    favorite_rows = session.query(WatchHistory.media_item_id, WatchHistory.favorite).filter(
        WatchHistory.media_item_id.in_(series_ids)
    ).all()
    favorite_map = {media_item_id: bool(favorite) for media_item_id, favorite in favorite_rows}
    return {
        row.id: {
            "imdb_id": row.imdb_id,
            "tmdb_id": row.tmdb_id,
            "favorite": favorite_map.get(row.id, False),
        }
        for row in series_rows
    }


def _series_poster_ids(media_item: MediaItem, series_map: dict) -> tuple:
    if media_item.media_type != "episode" or not media_item.series_id:
        return None, None
    series = series_map.get(media_item.series_id)
    if not series:
        return None, None
    return series.get("imdb_id"), series.get("tmdb_id")


def _favorited_series_ids(session: Session) -> List[int]:
    rows = (
        session.query(WatchHistory.media_item_id)
        .join(MediaItem, MediaItem.id == WatchHistory.media_item_id)
        .filter(MediaItem.media_type == "tvshow", WatchHistory.favorite.is_(True))
        .all()
    )
    return [row[0] for row in rows]


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

    # 按媒体类型过滤。电视剧筛选项同时匹配剧集(episode)；父项 tvshow 不出现在列表中。
    if media_type == "tvshow":
        query = query.filter(MediaItem.media_type == "episode")
    elif media_type:
        query = query.filter(MediaItem.media_type == media_type)
    else:
        query = query.filter(MediaItem.media_type != "tvshow")

    # 没有季/集号的条目（剧下挂的剧场版、特典等）不在列表展示
    query = query.filter(
        (MediaItem.media_type != "episode")
        | (
            (MediaItem.season_number >= 0)
            & (MediaItem.episode_number >= 0)
        )
    )

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

    # 按收藏状态过滤。剧集收藏包含：本集收藏，或父剧收藏。
    if favorite is not None:
        favorited_series_ids = _favorited_series_ids(session)
        if favorite:
            if favorited_series_ids:
                query = query.filter(
                    (watch_info.c.favorite > 0)
                    | MediaItem.series_id.in_(favorited_series_ids)
                )
            else:
                query = query.filter(watch_info.c.favorite > 0)
        else:
            if favorited_series_ids:
                query = query.filter(
                    ((watch_info.c.favorite == 0) | watch_info.c.favorite.is_(None))
                    & (
                        MediaItem.series_id.is_(None)
                        | ~MediaItem.series_id.in_(favorited_series_ids)
                    )
                )
            else:
                query = query.filter(
                    (watch_info.c.favorite == 0) | watch_info.c.favorite.is_(None)
                )

    # 获取总数
    count = query.count()

    # 应用排序
    sort_column = getattr(MediaItem, sort_by, MediaItem.updatetime)
    query = query.order_by(desc(sort_column) if sort_desc else asc(sort_column))

    # 分页
    results = query.offset(skip).limit(limit).all()

    metadata_service = MetadataService(session)
    crop_map = metadata_service.get_crop_by_numbers(
        [media_item.number for media_item, *_ in results],
    )
    series_map = _series_info_map(session, [media_item for media_item, *_ in results])

    # 构造结果
    items = []
    for media_item, favorite, watched, total_plays, play_progress, duration, has_rating, rating, watch_updatetime in results:
        item_dict = schemas.MediaItemInDB.model_validate(media_item)
        series_imdb_id, series_tmdb_id = _series_poster_ids(media_item, series_map)
        series_favorite = bool(
            media_item.series_id and series_map.get(media_item.series_id, {}).get("favorite")
        )

        # 创建用户数据对象
        userdata = schemas.UserWatchData(
            favorite=bool(favorite) or series_favorite,
            watched=watched or False,
            total_plays=total_plays or 0,
            play_progress=play_progress,
            duration=duration,
            has_rating=has_rating or False,
            user_rating=rating,
            last_played=watch_updatetime,
            watch_updatetime=watch_updatetime
        )

        crop = metadata_service.resolve_crop(media_item.number, crop_map)

        # 创建带有用户数据的媒体项
        item_with_watches = schemas.MediaItemWithWatches(
            **item_dict.model_dump(),
            userdata=userdata,
            crop=crop,
            series_imdb_id=series_imdb_id,
            series_tmdb_id=series_tmdb_id,
        )

        items.append(item_with_watches)

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
    media_item = session.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="媒体项不存在")
    
    # 查询观看历史信息
    watch_history = session.query(WatchHistory).filter(
        WatchHistory.media_item_id == media_id
    ).first()
    
    # 构建MediaItemWithWatches响应
    item_dict = schemas.MediaItemInDB.model_validate(media_item)
    series_map = _series_info_map(session, [media_item])
    series_imdb_id, series_tmdb_id = _series_poster_ids(media_item, series_map)
    series_favorite = bool(
        media_item.series_id and series_map.get(media_item.series_id, {}).get("favorite")
    )
    
    if watch_history:
        userdata = schemas.UserWatchData(
            favorite=(watch_history.favorite or False) or series_favorite,
            watched=watch_history.watched or False,
            total_plays=watch_history.watch_count or 0,
            play_progress=watch_history.play_progress,
            duration=watch_history.duration,
            has_rating=watch_history.has_rating or False,
            user_rating=watch_history.rating,
            last_played=watch_history.updatetime,
            watch_updatetime=watch_history.updatetime
        )
    else:
        userdata = schemas.UserWatchData(
            favorite=series_favorite,
            watched=False,
            total_plays=0
        )
    
    return schemas.MediaItemWithWatches(
        **item_dict.model_dump(),
        userdata=userdata,
        crop=MetadataService(session).get_crop_by_number(media_item.number),
        series_imdb_id=series_imdb_id,
        series_tmdb_id=series_tmdb_id,
    )


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
    media_item = session.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="媒体项不存在")

    update_data = media_item_in.model_dump(exclude_unset=True)
    
    # 分离观看历史相关的字段
    watch_fields = ['watched', 'favorite', 'play_progress', 'duration', 'has_rating', 'user_rating']
    watch_data = {k: v for k, v in update_data.items() if k in watch_fields}
    media_data = {k: v for k, v in update_data.items() if k not in watch_fields}
    
    # 更新媒体项基础信息
    for field, value in media_data.items():
        setattr(media_item, field, value)
    
    # 如果有观看历史相关的更新，处理WatchHistory表
    if watch_data:
        # 查找或创建WatchHistory记录
        watch_history = session.query(WatchHistory).filter(
            WatchHistory.media_item_id == media_id
        ).first()
        
        if not watch_history:
            # 创建新的观看历史记录
            watch_history = WatchHistory(media_item_id=media_id)
            session.add(watch_history)
        
        # 更新观看历史字段
        if 'watched' in watch_data:
            watch_history.watched = watch_data['watched']
        if 'favorite' in watch_data:
            watch_history.favorite = watch_data['favorite']
        if 'play_progress' in watch_data:
            watch_history.play_progress = watch_data['play_progress']
        if 'duration' in watch_data:
            watch_history.duration = watch_data['duration']
        if 'has_rating' in watch_data:
            watch_history.has_rating = watch_data['has_rating']
        if 'user_rating' in watch_data:
            watch_history.rating = watch_data['user_rating']
    
    session.commit()
    session.refresh(media_item)
    
    # 查询观看历史信息，构建返回结果
    watch_history = session.query(WatchHistory).filter(
        WatchHistory.media_item_id == media_id
    ).first()
    
    # 构建MediaItemWithWatches响应
    item_dict = schemas.MediaItemInDB.model_validate(media_item)
    series_map = _series_info_map(session, [media_item])
    series_imdb_id, series_tmdb_id = _series_poster_ids(media_item, series_map)
    series_favorite = bool(
        media_item.series_id and series_map.get(media_item.series_id, {}).get("favorite")
    )

    if watch_history:
        userdata = schemas.UserWatchData(
            favorite=(watch_history.favorite or False) or series_favorite,
            watched=watch_history.watched or False,
            total_plays=watch_history.watch_count or 0,
            play_progress=watch_history.play_progress,
            duration=watch_history.duration,
            has_rating=watch_history.has_rating or False,
            user_rating=watch_history.rating,
            last_played=watch_history.updatetime,
            watch_updatetime=watch_history.updatetime
        )
    else:
        userdata = schemas.UserWatchData(
            favorite=series_favorite,
            watched=False,
            total_plays=0
        )
    
    return schemas.MediaItemWithWatches(
        **item_dict.model_dump(),
        userdata=userdata,
        crop=MetadataService(session).get_crop_by_number(media_item.number),
        series_imdb_id=series_imdb_id,
        series_tmdb_id=series_tmdb_id,
    )


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
