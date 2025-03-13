from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .media_item import MediaItemInDB


class WatchHistoryBase(BaseModel):
    """
    观看历史基础属性
    """
    source: str
    external_id: str
    media_item_id: int
    
    played_at: Optional[datetime] = None
    play_count: Optional[int] = 1
    play_progress: Optional[float] = 100.0
    duration: Optional[int] = None
    
    rating: Optional[float] = 0.0
    has_rating: Optional[bool] = False


class WatchHistoryCreate(WatchHistoryBase):
    """
    创建观看历史时的属性
    """
    pass


class WatchHistoryUpdate(BaseModel):
    """
    更新观看历史时的属性
    """
    source: Optional[str] = None
    external_id: Optional[str] = None
    media_item_id: Optional[int] = None
    played_at: Optional[datetime] = None
    play_count: Optional[int] = None
    play_progress: Optional[float] = None
    duration: Optional[int] = None
    rating: Optional[float] = None
    has_rating: Optional[bool] = None


class WatchHistoryInDB(WatchHistoryBase):
    """
    数据库中的观看历史属性
    """
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WatchHistoryWithMedia(WatchHistoryInDB):
    """
    包含媒体信息的观看历史
    """
    media_item: MediaItemInDB

    class Config:
        from_attributes = True


class WatchHistoryCollection(BaseModel):
    """
    观看历史集合，用于分页响应
    """
    data: List[WatchHistoryWithMedia]
    count: int 