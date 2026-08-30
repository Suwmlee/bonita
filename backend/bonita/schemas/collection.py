from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, model_validator

from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.schemas.mediaitem import MediaItemWithWatches


def _resolve_external_id(external_id: Optional[str], emby_id: Optional[str]) -> str:
    return (external_id or emby_id or "").strip()


class EmbyCollectionCandidate(BaseModel):
    source: str = SOURCE_EMBY
    external_id: str = ""
    emby_id: str = ""
    name: str
    child_count: int = 0
    image_tag: Optional[str] = None
    added: bool = False

    @model_validator(mode="after")
    def fill_id_aliases(self):
        rid = _resolve_external_id(self.external_id, self.emby_id)
        self.external_id = rid
        self.emby_id = rid
        return self


class CollectionCreate(BaseModel):
    source: str = SOURCE_EMBY
    external_id: Optional[str] = None
    emby_id: Optional[str] = None
    name: Optional[str] = None

    @property
    def resolved_id(self) -> str:
        return _resolve_external_id(self.external_id, self.emby_id)


class CollectionAddItems(BaseModel):
    media_item_ids: List[int]


class CollectionPublic(BaseModel):
    id: int
    source: str = SOURCE_EMBY
    external_id: str = ""
    emby_id: str = ""
    name: str
    image_tag: Optional[str] = None
    item_count: int = 0
    matched_count: int = 0
    last_sync_at: Optional[datetime] = None
    createtime: datetime
    updatetime: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def fill_id_aliases(self):
        rid = _resolve_external_id(self.external_id, self.emby_id)
        self.external_id = rid
        self.emby_id = rid
        return self


class CollectionCollection(BaseModel):
    data: List[CollectionPublic]
    count: int


class CollectionDetail(CollectionPublic):
    items: List[MediaItemWithWatches] = []
