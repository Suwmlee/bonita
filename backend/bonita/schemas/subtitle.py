from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubtitlePublic(BaseModel):
    id: int
    media_item_id: Optional[int] = None
    media_type: str = ""
    number: str = ""
    title: str = ""
    series_title: str = ""
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    language: str = "zh-Hans"
    part_number: int = 0
    original_name: str = ""
    file_extension: str = ""
    preferred: bool = False
    file_size: Optional[int] = None
    createtime: Optional[datetime] = None
    updatetime: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubtitleCollection(BaseModel):
    data: List[SubtitlePublic]
    count: int


class SubtitleGroupPublic(BaseModel):
    key: str
    media_item_id: Optional[int] = None
    media_type: str = ""
    number: str = ""
    title: str = ""
    imdb_id: str = ""
    tmdb_id: str = ""
    crop: bool = True
    count: int = 0
    subtitles: List[SubtitlePublic] = Field(default_factory=list)


class SubtitleGroupCollection(BaseModel):
    data: List[SubtitleGroupPublic]
    count: int


class SubtitleUploadResult(BaseModel):
    data: List[SubtitlePublic]
    unmatched: int = 0
    replaced: int = 0
    failed: List[str] = []


class SubtitleUpdate(BaseModel):
    media_item_id: Optional[int] = None
    number: str = ""
    language: str = "zh-Hans"
    part_number: int = Field(default=0, ge=0)


class SubtitleDeliverRequest(BaseModel):
    media_item_ids: List[int] = Field(default_factory=list)
    part_number: Optional[int] = Field(default=None, ge=0)
    overwrite: bool = False


class SubtitleDeliverResult(BaseModel):
    copied: int = 0
    skipped: int = 0
    missing: int = 0
    failed: int = 0
    details: List[str] = Field(default_factory=list)


class SubtitleRetransferResult(BaseModel):
    started: int = 0
