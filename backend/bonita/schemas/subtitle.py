from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubtitlePublic(BaseModel):
    id: int
    identity_type: str = "number"
    identity_key: str = ""
    language: str = "zh-Hans"
    part_number: int = 0
    original_name: str = ""
    file_extension: str = ""
    createtime: Optional[datetime] = None
    updatetime: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubtitleCollection(BaseModel):
    data: List[SubtitlePublic]
    count: int


class SubtitleUploadResult(BaseModel):
    data: List[SubtitlePublic]
    unmatched: int = 0
    replaced: int = 0
    failed: List[str] = []


class SubtitleUpdate(BaseModel):
    identity_key: str = ""
    language: str = "zh-Hans"
    part_number: int = Field(default=0, ge=0)


class SubtitleDeliverRequest(BaseModel):
    number: str
    part_number: Optional[int] = Field(default=None, ge=0)
    overwrite: bool = False


class SubtitleDeliverResult(BaseModel):
    copied: int = 0
    skipped: int = 0
    missing: int = 0
