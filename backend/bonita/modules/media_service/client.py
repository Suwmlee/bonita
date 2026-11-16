from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, runtime_checkable


SOURCE_EMBY = "emby"
SOURCE_PLEX = "plex"

DIR_FROM_SERVER = "from_server"
DIR_TO_SERVER = "to_server"

# 统一评分 0–10。喜爱 = 至少 9 分（4.5 星）。无精确分时「标记喜爱」写 10。
RATING_FAVORITE_MIN = 9.0
RATING_FAVORITE_WRITE = 10.0

_SOURCE_LABELS = {
    SOURCE_EMBY: "Emby",
    SOURCE_PLEX: "Plex",
}


def is_favorite_rating(rating) -> bool:
    try:
        return rating is not None and float(rating) >= RATING_FAVORITE_MIN
    except (TypeError, ValueError):
        return False


def normalize_favorite(favorite: bool = False, rating=None) -> bool:
    """喜爱：显式收藏，或评分达到阈值。"""
    return bool(favorite) or is_favorite_rating(rating)


def source_label(source: str) -> str:
    return _SOURCE_LABELS.get(source, source or "媒体服务器")


def is_to_server(direction: str) -> bool:
    return direction == DIR_TO_SERVER


ITEM_MOVIE = "movie"
ITEM_VIDEO = "video"
ITEM_EPISODE = "episode"
ITEM_SERIES = "series"
ITEM_SEASON = "season"
ITEM_COLLECTION = "collection"
ITEM_TRACK = "track"

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
    # 用户评分 0–10；None/0 表示未评分（Plex/Trakt 等以评分为主）
    rating: Optional[float] = None


@dataclass
class RemoteItem:
    source: str
    remote_id: str
    item_type: str
    title: str = ""
    original_title: str = ""
    path: Optional[str] = None
    source_paths: List[str] = field(default_factory=list)
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
class PlaylistRef:
    """远端播放列表引用；smart=True 时可拉不可直接改成员。"""
    remote_id: str
    rating_key: str
    name: str
    guid: str = ""
    leaf_count: int = 0
    playlist_type: str = "audio"
    smart: bool = False


@dataclass
class PlaylistTrack:
    """播放列表成员快照。允许尚未对上本地媒体项。"""
    rating_key: str
    title: str = ""
    artist: str = ""
    album: str = ""
    guid: str = ""
    path: Optional[str] = None
    playlist_item_id: Optional[str] = None
    sort_index: int = 0


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


@runtime_checkable
class CollectionCapable(Protocol):
    """合集（BoxSet）能力；当前由 Emby 实现。"""

    def search_collections(self, search: str = "", limit: int = 50) -> List[CollectionRef]:
        ...

    def get_collection_items(self, collection_id: str) -> List[RemoteItem]:
        ...

    def add_items_to_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        ...

    def remove_items_from_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        ...


@runtime_checkable
class PlaylistCapable(Protocol):
    """音频播放列表能力；当前由 Plex 实现。"""

    def list_audio_playlists(
        self,
        search: str = "",
        limit: int = 50,
        include_smart: bool = True,
    ) -> List[PlaylistRef]:
        ...

    def get_playlist(self, rating_key: str) -> Optional[PlaylistRef]:
        ...

    def create_audio_playlist(self, title: str, track_rating_keys: List[str]) -> PlaylistRef:
        ...

    def get_playlist_items(self, rating_key: str) -> List[PlaylistTrack]:
        ...

    def add_items_to_playlist(self, playlist_rating_key: str, track_rating_keys: List[str]) -> tuple:
        ...

    def remove_items_from_playlist(self, playlist_rating_key: str, playlist_item_ids: List[str]) -> tuple:
        ...
