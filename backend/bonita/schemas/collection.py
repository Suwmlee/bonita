from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.schemas.mediaitem import MediaItemWithWatches


class EmbyCollectionCandidate(BaseModel):
    source: str = SOURCE_EMBY
    external_id: str
    name: str
    child_count: int = 0
    image_tag: Optional[str] = None
    added: bool = False


class CollectionCreate(BaseModel):
    source: str = SOURCE_EMBY
    external_id: str
    name: Optional[str] = None


class CollectionAddItems(BaseModel):
    media_item_ids: List[int]


class CollectionPublic(BaseModel):
    id: int
    source: str = SOURCE_EMBY
    external_id: str
    name: str
    image_tag: Optional[str] = None
    item_count: int = 0
    matched_count: int = 0
    last_sync_at: Optional[datetime] = None
    createtime: datetime
    updatetime: datetime

    class Config:
        from_attributes = True


class CollectionCollection(BaseModel):
    data: List[CollectionPublic]
    count: int


class CollectionDetail(CollectionPublic):
    items: List[MediaItemWithWatches] = []
