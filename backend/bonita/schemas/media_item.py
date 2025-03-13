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
    year: Optional[int] = None
    
    # 标识符
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    douban_id: Optional[str] = None
    number: Optional[str] = None
    
    # 剧集信息
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    
    # 图片
    poster: Optional[str] = None


class MediaItemCreate(MediaItemBase):
    """
    创建MediaItem时的属性
    """
    pass


class MediaItemUpdate(BaseModel):
    """
    更新MediaItem时的属性
    """
    media_type: Optional[str] = None
    title: Optional[str] = None
    original_title: Optional[str] = None
    year: Optional[int] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    douban_id: Optional[str] = None
    number: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    poster: Optional[str] = None
    series_id: Optional[int] = None


class MediaItemInDB(MediaItemBase):
    """
    数据库中的MediaItem属性
    """
    id: int
    series_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MediaItemWithWatches(MediaItemInDB):
    """
    包含观看历史的MediaItem
    """
    total_plays: int = 0
    last_played: Optional[datetime] = None
    user_rating: Optional[float] = None
    
    class Config:
        from_attributes = True


class MediaItemCollection(BaseModel):
    """
    MediaItem集合，用于分页响应
    """
    data: List[MediaItemInDB]
    count: int 