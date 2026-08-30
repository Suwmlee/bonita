import logging
from typing import List, Optional

from bonita.modules.media_service.client import (
    SOURCE_JELLYFIN,
    WEBHOOK_IGNORED,
    CollectionRef,
    MediaServerClient,
    RemoteItem,
    WebhookEvent,
)
from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class JellyfinClient(MediaServerClient, metaclass=Singleton):
    """Jellyfin 适配器架子。未接线，initialize 不会连上服务器。"""

    source = SOURCE_JELLYFIN

    def __init__(self):
        self.host = ""
        self.apikey = ""
        self.user = ""
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def configured_user(self) -> str:
        return self.user or ""

    def initialize(self, host: str, apikey: str, user: str = "") -> bool:
        self.host, self.apikey, self.user = host or "", apikey or "", user or ""
        self._initialized = False
        logger.info("JellyfinClient is a stub; skip initialize")
        return False

    def trigger_library_scan(self):
        logger.warning("JellyfinClient.trigger_library_scan is not implemented")

    def list_user_items(self) -> List[RemoteItem]:
        return []

    def get_item(self, item_id: str) -> Optional[RemoteItem]:
        return None

    def get_user_item(self, item_id: str) -> Optional[RemoteItem]:
        return None

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
        return []

    def search_collections(self, search: str = "", limit: int = 50) -> List[CollectionRef]:
        return []

    def get_collection_items(self, collection_id: str) -> List[RemoteItem]:
        return []

    def add_items_to_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        return 0, len(item_ids)

    def remove_items_from_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        return 0, len(item_ids)

    def mark_as_played(self, item_id: str):
        return None

    def mark_as_unplayed(self, item_id: str):
        return None

    def mark_as_favorite(self, item_id: str):
        return None

    def unmark_as_favorite(self, item_id: str):
        return None

    def get_item_image_url(self, item_id: str, image_tag: str = None, size: str = "w500") -> Optional[str]:
        return None

    def get_poster_url(
        self,
        title: str,
        imdb_id: str = None,
        tmdb_id=None,
        size: str = "w500",
    ) -> Optional[str]:
        return None

    def parse_webhook(self, payload: dict) -> WebhookEvent:
        return WebhookEvent(kind=WEBHOOK_IGNORED)
