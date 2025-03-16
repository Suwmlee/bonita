from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class MediaItemBase(BaseModel):
    """
    MediaItem的基础属性
    """
    media_type: str
    title: str
    original_title: Optional[str] = None

    # 标识符
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    number: Optional[str] = None

    # 剧集信息
    season_number: Optional[int] = None
    episode_number: Optional[int] = None


class MediaItemCreate(MediaItemBase):
    """
    创建MediaItem时的属性
    """
    series_id: Optional[int] = None


class MediaItemUpdate(BaseModel):
    """
    更新MediaItem时的属性
    """
    media_type: Optional[str] = None
    title: Optional[str] = None
    original_title: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    number: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    series_id: Optional[int] = None


class MediaItemInDB(MediaItemBase):
    """
    数据库中的MediaItem属性
    """
    id: int
    series_id: Optional[int] = None
    createtime: datetime
    updatetime: datetime

    class Config:
        from_attributes = True


class UserWatchData(BaseModel):
    """
    用户观看数据，用于嵌套在MediaItem中
    """
    # 基本观看状态
    watched: Optional[bool] = False
    favorite: Optional[bool] = False

    # 详细观看信息
    total_plays: int = 0
    play_progress: Optional[float] = None
    duration: Optional[int] = None

    # 评分信息
    has_rating: Optional[bool] = False
    user_rating: Optional[float] = None

    # 时间信息
    last_played: Optional[datetime] = None
    watch_updatetime: Optional[datetime] = None

    class Config:
        from_attributes = True


class MediaItemWithWatches(MediaItemInDB):
    """
    包含观看历史的MediaItem
    """
    userdata: Optional[UserWatchData] = None

    class Config:
        from_attributes = True


class MediaItemCollection(BaseModel):
    """
    MediaItem集合，用于分页响应
    """
    data: List[MediaItemWithWatches]
    count: int
