from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


SOURCE_EMBY = "emby"
SOURCE_JELLYFIN = "jellyfin"

DIR_FROM_SERVER = "from_server"
DIR_TO_SERVER = "to_server"

_SOURCE_LABELS = {
    SOURCE_EMBY: "Emby",
    SOURCE_JELLYFIN: "Jellyfin",
}


def source_label(source: str) -> str:
    return _SOURCE_LABELS.get(source, source or "媒体服务器")


def is_to_server(direction: str) -> bool:
    return direction in ("to_emby", "to_server", "to_jellyfin")


ITEM_MOVIE = "movie"
ITEM_VIDEO = "video"
ITEM_EPISODE = "episode"
ITEM_SERIES = "series"
ITEM_SEASON = "season"
ITEM_COLLECTION = "collection"

WEBHOOK_TEST = "test"
WEBHOOK_IGNORED = "ignored"
WEBHOOK_WATCH = "watch"
WEBHOOK_UNPLAYED = "unplayed"
WEBHOOK_FAVORITE = "favorite"
WEBHOOK_LIBRARY_NEW = "library_new"


@dataclass
class WatchState:
    played: bool = False
    favorite: bool = False
    play_count: int = 1
    position_seconds: int = 0
    duration_seconds: int = 0
    play_progress: float = 0.0


@dataclass
class RemoteItem:
    source: str
    remote_id: str
    item_type: str
    title: str = ""
    original_title: str = ""
    path: Optional[str] = None
    provider_ids: Dict[str, str] = field(default_factory=dict)
    season: int = -1
    episode: int = -1
    series_remote_id: Optional[str] = None
    series_name: str = ""
    watch: Optional[WatchState] = None
    image_tag: Optional[str] = None
    child_count: int = 0
    is_folder: bool = False

    @property
    def imdb_id(self) -> str:
        return self.provider_ids.get("imdb") or ""

    @property
    def tmdb_id(self) -> str:
        return self.provider_ids.get("tmdb") or ""

    @property
    def tvdb_id(self) -> str:
        return self.provider_ids.get("tvdb") or ""


@dataclass
class CollectionRef:
    remote_id: str
    name: str
    child_count: int = 0
    image_tag: Optional[str] = None


@dataclass
class WebhookEvent:
    kind: str
    user_name: str = ""
    items: List[RemoteItem] = field(default_factory=list)
    raw_event: str = ""


class MediaServerClient(ABC):
    """媒体服务器协议适配器。同步业务只依赖这里的归一化类型。"""

    source: str = ""

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        pass

    @property
    def configured_user(self) -> str:
        return ""

    @abstractmethod
    def initialize(self, host: str, apikey: str, user: str = "") -> bool:
        pass

    @abstractmethod
    def trigger_library_scan(self):
        pass

    @abstractmethod
    def list_user_items(self) -> List[RemoteItem]:
        pass

    @abstractmethod
    def get_item(self, item_id: str) -> Optional[RemoteItem]:
        pass

    @abstractmethod
    def get_user_item(self, item_id: str) -> Optional[RemoteItem]:
        pass

    @abstractmethod
    def query_items(
        self,
        item_types: List[str],
        search_term: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[str] = None,
        tvdb_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        limit: int = 25,
    ) -> List[RemoteItem]:
        pass

    @abstractmethod
    def search_collections(self, search: str = "", limit: int = 50) -> List[CollectionRef]:
        pass

    @abstractmethod
    def get_collection_items(self, collection_id: str) -> List[RemoteItem]:
        pass

    @abstractmethod
    def add_items_to_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        pass

    @abstractmethod
    def remove_items_from_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        pass

    @abstractmethod
    def mark_as_played(self, item_id: str):
        pass

    @abstractmethod
    def mark_as_unplayed(self, item_id: str):
        pass

    @abstractmethod
    def mark_as_favorite(self, item_id: str):
        pass

    @abstractmethod
    def unmark_as_favorite(self, item_id: str):
        pass

    @abstractmethod
    def get_item_image_url(self, item_id: str, image_tag: str = None, size: str = "w500") -> Optional[str]:
        pass

    @abstractmethod
    def get_poster_url(
        self,
        title: str,
        imdb_id: str = None,
        tmdb_id=None,
        size: str = "w500",
    ) -> Optional[str]:
        pass

    @abstractmethod
    def parse_webhook(self, payload: dict) -> WebhookEvent:
        pass
