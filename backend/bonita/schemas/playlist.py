from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from bonita.modules.media_service.client import SOURCE_PLEX


class PlexPlaylistCandidate(BaseModel):
    source: str = SOURCE_PLEX
    external_id: str
    rating_key: str
    name: str
    leaf_count: int = 0
    smart: bool = False
    added: bool = False


class PlaylistCreate(BaseModel):
    source: str = SOURCE_PLEX
    external_id: str
    rating_key: Optional[str] = None
    name: Optional[str] = None


class PlaylistItemPublic(BaseModel):
    id: int
    playlist_id: int
    media_item_id: Optional[int] = None
    external_item_id: Optional[str] = None
    external_guid: Optional[str] = None
    playlist_item_id: Optional[str] = None
    path: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    sort_index: int = 0

    class Config:
        from_attributes = True


class PlaylistPublic(BaseModel):
    id: int
    source: str = SOURCE_PLEX
    external_id: str
    rating_key: Optional[str] = None
    write_rating_key: Optional[str] = None
    name: str
    is_smart: bool = False
    item_count: int = 0
    matched_count: int = 0
    last_sync_at: Optional[datetime] = None
    createtime: datetime
    updatetime: datetime

    class Config:
        from_attributes = True


class PlaylistCollection(BaseModel):
    data: List[PlaylistPublic]
    count: int


class PlaylistDetail(PlaylistPublic):
    items: List[PlaylistItemPublic] = []
