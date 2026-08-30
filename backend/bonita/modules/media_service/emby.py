import logging
import requests
from typing import Any, Dict, List, Optional, Union

from bonita.modules.media_service.client import (
    ITEM_COLLECTION,
    ITEM_EPISODE,
    ITEM_MOVIE,
    ITEM_SEASON,
    ITEM_SERIES,
    ITEM_VIDEO,
    SOURCE_EMBY,
    WEBHOOK_FAVORITE,
    WEBHOOK_IGNORED,
    WEBHOOK_LIBRARY_NEW,
    WEBHOOK_TEST,
    WEBHOOK_UNPLAYED,
    WEBHOOK_WATCH,
    CollectionRef,
    MediaServerClient,
    RemoteItem,
    WatchState,
    WebhookEvent,
)
from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)

_EMBY_TYPE_MAP = {
    "Movie": ITEM_MOVIE,
    "Video": ITEM_VIDEO,
    "Episode": ITEM_EPISODE,
    "Series": ITEM_SERIES,
    "Season": ITEM_SEASON,
    "BoxSet": ITEM_COLLECTION,
}
_TYPE_TO_EMBY = {
    ITEM_MOVIE: "Movie",
    ITEM_VIDEO: "Video",
    ITEM_EPISODE: "Episode",
    ITEM_SERIES: "Series",
    ITEM_SEASON: "Season",
    ITEM_COLLECTION: "BoxSet",
}
_WEBHOOK_WATCH_EVENTS = {
    "playback.stop",
    "playback.scrobble",
    "item.markplayed",
}
_WEBHOOK_LIBRARY_EVENTS = {"library.new", "item.added"}


def _ticks_to_seconds(ticks) -> int:
    if not ticks:
        return 0
    try:
        ticks = int(ticks)
    except (TypeError, ValueError):
        return 0
    if ticks <= 0:
        return 0
    return int(ticks / 10000000)


def _as_int(value, default=-1) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class EmbyClient(MediaServerClient, metaclass=Singleton):
    """Emby HTTP 适配器。对外只暴露归一化类型。"""

    source = SOURCE_EMBY

    def __init__(self):
        self.emby_host = None
        self.emby_apikey = None
        self.emby_user = None
        self.emby_user_id = None
        self.headers = {}
        self._initialized = False

    def initialize(self, host: str, apikey: str, user: str = "") -> bool:
        """Initialize the Emby service with connection parameters
        """
        emby_host, emby_apikey, emby_user = host or "", apikey or "", user or ""
        # 如果已经初始化并且参数相同，直接返回 True
        if (self._initialized and
            self.emby_host == emby_host.rstrip('/') and
            self.emby_apikey == emby_apikey and
            self.emby_user == emby_user.lower()):
            return True

        self.emby_host = emby_host.rstrip('/') if emby_host else None
        self.emby_apikey = emby_apikey
        self.headers = {
            "X-Emby-Token": self.emby_apikey,
            "Content-Type": "application/json"
        }
        if not self.emby_host or not self.emby_apikey or not emby_user:
            logger.warning("Emby service initialized with missing host, API key or user")
            self._initialized = False
            return False
        try:
            self.emby_user = emby_user.lower()
            self.emby_user_id = self.get_users().get(self.emby_user)
            if not self.emby_user_id:
                logger.warning(f"User {self.emby_user} not found in Emby")
                self._initialized = False
                return False
            self._initialized = True
        except Exception as e:
            logger.error(f"Error initializing Emby service: {e}")
            self._initialized = False
            return False
        logger.info(f"Emby service initialized with host: {self.emby_host}, user: {self.emby_user}")
        return True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def configured_user(self) -> str:
        return self.emby_user or ""

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        expected_status_codes: Optional[List[int]] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]], bool, None]:
        """Make a request to the Emby API

        Args:
            method (str): HTTP method (get, post, etc.)
            endpoint (str): API endpoint (without host)
            data (dict, optional): Request body for POST requests
            expected_status_codes (list, optional): List of expected status codes

        Returns:
            dict, list, bool or None: Response data if successful, True for successful status codes with no content
        """
        if not self.emby_host or not self.emby_apikey:
            raise Exception("Emby host or API key not configured")
        # Ensure endpoint starts with / if needed
        if not endpoint.startswith('/'):
            endpoint = f"/{endpoint}"

        # Construct full URL
        url = f"{self.emby_host}{endpoint}"
        if expected_status_codes is None:
            expected_status_codes = [200, 204]
        try:
            # Use the session for better performance with connection pooling
            response = requests.request(
                method=method.lower(),
                url=url,
                json=data if data is not None else None,
                headers=self.headers,
                params=params
            )

            if response.status_code in expected_status_codes:
                if response.status_code == 204 or not response.text:
                    return True
                result = response.json() if response.text else True
                return result
            else:
                logger.error(f"Failed Emby API request. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Failed Emby API request to {endpoint}. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during Emby API request: {str(e)}")
            raise

    def trigger_library_scan(self):
        """Triggers a library scan in Emby
        """
        return self._make_request('post', '/Library/Refresh')

    def get_server_info(self):
        """Get server information
        """
        return self._make_request('get', '/System/Info/Public')

    def get_users(self):
        """Get all users from Emby
        """
        users = {}
        response = self._make_request('get', '/emby/Users')
        if isinstance(response, list):
            for user in response:
                users[user.get("Name").lower()] = user.get("Id")
        return users

    def get_user_libraries(self, user_id: str) -> dict[str, Any]:
        """Get all libraries from Emby for the configured user
        """
        libraries = {}
        # Get views (libraries) for the user
        response = self._make_request('get', f'/Users/{user_id}/Views')

        if not isinstance(response, dict):
            logger.error("Failed to get libraries, unexpected response format")
            return libraries
        for library in response.get("Items", []):
            library_id = library.get("Id")
            library_name = library.get("Name")
            library_type = library.get("CollectionType")
            # Only include movie and TV show libraries
            if library_type in ["movies", "tvshows"]:
                libraries[library_id] = {
                    "name": library_name,
                    "type": library_type
                }
            else:
                logger.debug(f"Skipping library {library_name} with type {library_type}")

        return libraries

    def get_user_library_items(self, library_id: str, library_type: str, user_id: str) -> dict[str, Any]:
        """Get items for a library
        """
        if not library_id or not user_id:
            return None

        result = {
            "movies": [],
            "series": [],
            "seasons": [],
            "episodes": [],
        }

        # Get movies
        if library_type == "movies" or not library_type:
            # Get fully movies
            matched_movies = self._make_request(
                'get',
                f'/Users/{user_id}/Items',
                params={
                    "ParentId": library_id,
                    "IncludeItemTypes": "Movie",
                    "Recursive": "True",
                    "Fields": "ItemCounts,ProviderIds,Path,DateCreated,UserDataLastPlayedDate"
                }
            )

            if isinstance(matched_movies, dict) and matched_movies.get("Items"):
                result["movies"].extend(matched_movies.get("Items", []))

        # Get TV shows and episodes
        if library_type == "tvshows" or not library_type:
            # Get all shows in the library
            all_shows = self._make_request(
                'get',
                f'/Users/{user_id}/Items',
                params={
                    "ParentId": library_id,
                    "isPlaceHolder": "false",
                    "IncludeItemTypes": "Series",
                    "Recursive": "True",
                    "Fields": "ProviderIds,Path,RecursiveItemCount,UserData"
                }
            )

            if isinstance(all_shows, dict) and all_shows.get("Items"):
                for show in all_shows.get("Items", []):
                    result["series"].append(show)
                    show_id = show.get("Id")
                    seasons = self._make_request(
                        'get',
                        f'/Shows/{show_id}/Seasons',
                        params={
                            "userId": user_id,
                            "Fields": "UserData,ProviderIds,IndexNumber,SeriesName,SeriesId",
                        }
                    )
                    if isinstance(seasons, dict) and seasons.get("Items"):
                        result["seasons"].extend(seasons.get("Items", []))
                    show_episodes = self._make_request(
                        'get',
                        f'/Shows/{show_id}/Episodes',
                        params={
                            "userId": user_id,
                            "isPlaceHolder": "false",
                            "Fields": "ProviderIds,Path,DateCreated,UserDataLastPlayedDate,SeriesName,SeriesId,IndexNumber,ParentIndexNumber,RunTimeTicks"
                        }
                    )

                    if isinstance(show_episodes, dict) and show_episodes.get("Items"):
                        result["episodes"].extend(show_episodes.get("Items", []))

        return result

    def get_user_all_items(self, user_id=None) -> dict[str, Any]:
        """Get all items for a user across all libraries
        """
        if not user_id:
            user_id = self.emby_user_id
        if not user_id:
            logger.warning("No user ID available to fetch all items")
            return None

        # Get all libraries for the user
        libraries = self.get_user_libraries(user_id)
        if not libraries:
            logger.warning("No libraries found for user")
            return None

        result = {}

        # Get items for each library
        for library_id, library_info in libraries.items():
            library_name = library_info.get("name")
            library_type = library_info.get("type")
            if not library_name or not library_type:
                continue

            items = self.get_user_library_items(library_id, library_type, user_id)
            if items:
                result[library_id] = items

        return result

    def get_item_details(self, item_id) -> Dict[str, Any]:
        """按当前用户取单条详情。Emby 没有 GET /emby/Items/{id}，网页端用的是用户库接口。"""
        return self.get_user_item_details(item_id)

    def get_user_item_details(self, item_id, user_id=None) -> Dict[str, Any]:
        """按当前用户取条目，带 UserData（已看/收藏）。"""
        if not item_id:
            return None
        if not user_id:
            user_id = self.emby_user_id
        if not user_id:
            return None
        try:
            return self._make_request(
                "get",
                f"/Users/{user_id}/Items/{item_id}",
                params={
                    "Fields": (
                        "ProviderIds,Path,UserData,OriginalTitle,SeriesName,SeriesId,"
                        "IndexNumber,ParentIndexNumber,RunTimeTicks,ImageTags"
                    ),
                },
            )
        except Exception as e:
            logger.error(f"Error fetching Emby user item details: {str(e)}")
            return None

    def search_items(self, search_term, limit=50) -> Dict[str, Any]:
        """Search for items in Emby
        Args:
            search_term (str): Term to search for
            limit (int, optional): Maximum number of items to return
        """
        params = {
            "SearchTerm": search_term,
            "Limit": limit,
            "IncludeItemTypes": "Movie,Episode,Series"
        }
        return self._make_request('get', '/emby/Items', params=params)

    def search_boxsets(self, search_term: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """列出或搜索 Emby 合集（BoxSet），不写入本地。"""
        if not self.emby_user_id:
            return []
        params = {
            "Recursive": "True",
            "IncludeItemTypes": "BoxSet",
            "Fields": "ChildCount,RecursiveItemCount,ImageTags",
            "Limit": limit,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
        if search_term:
            params["SearchTerm"] = search_term
        response = self._make_request(
            "get",
            f"/Users/{self.emby_user_id}/Items",
            params=params,
        )
        if isinstance(response, dict):
            return response.get("Items") or []
        return []

    def get_boxset_items(self, boxset_id: str) -> List[Dict[str, Any]]:
        """获取合集的直接成员（电影 / 剧 / 集）。"""
        if not self.emby_user_id or not boxset_id:
            return []
        items: List[Dict[str, Any]] = []
        start = 0
        page_size = 200
        while True:
            response = self._make_request(
                "get",
                f"/Users/{self.emby_user_id}/Items",
                params={
                    "ParentId": boxset_id,
                    "Recursive": "False",
                    "IncludeItemTypes": "Movie,Episode,Series,Video",
                    "Fields": (
                        "ProviderIds,Path,SeriesName,SeriesId,"
                        "IndexNumber,ParentIndexNumber,RunTimeTicks"
                    ),
                    "StartIndex": start,
                    "Limit": page_size,
                },
            )
            page = response.get("Items") or [] if isinstance(response, dict) else []
            items.extend(page)
            if len(page) < page_size:
                break
            start += page_size
            if start >= 10000:
                break
        return items

    def _query_raw_items(
        self,
        include_item_types: str,
        search_term: str = None,
        provider_id_equals: str = None,
        parent_id: str = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """按类型 / 外部 ID / 关键词查找库内条目。"""
        if not self.emby_user_id:
            return []
        params: Dict[str, Any] = {
            "Recursive": "True",
            "IncludeItemTypes": include_item_types,
            "Fields": (
                "ProviderIds,Path,SeriesName,SeriesId,"
                "IndexNumber,ParentIndexNumber"
            ),
            "Limit": limit,
        }
        if search_term:
            params["SearchTerm"] = search_term
        if provider_id_equals:
            params["AnyProviderIdEquals"] = provider_id_equals
        if parent_id:
            params["ParentId"] = parent_id
        try:
            response = self._make_request(
                "get",
                f"/Users/{self.emby_user_id}/Items",
                params=params,
            )
        except Exception as e:
            logger.error(f"Error querying Emby items: {e}")
            return []
        if isinstance(response, dict):
            return response.get("Items") or []
        return []

    def add_items_to_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        """把条目加入 Emby 合集。返回 (成功数, 失败数)。"""
        return self._mutate_collection_items("post", collection_id, item_ids)

    def remove_items_from_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        """从 Emby 合集移除条目。返回 (成功数, 失败数)。"""
        return self._mutate_collection_items("delete", collection_id, item_ids)

    def _mutate_collection_items(self, method: str, collection_id: str, item_ids: List[str]) -> tuple:
        if not collection_id or not item_ids:
            return 0, 0
        unique_ids = list(dict.fromkeys(item_ids))
        succeeded = 0
        failed = 0
        for offset in range(0, len(unique_ids), 50):
            chunk = unique_ids[offset:offset + 50]
            try:
                self._make_request(
                    method,
                    f"/emby/Collections/{collection_id}/Items",
                    params={"Ids": ",".join(chunk)},
                    data=None,
                )
                succeeded += len(chunk)
            except Exception as e:
                if len(chunk) == 1:
                    logger.error(f"合集成员变更失败 {method} {chunk[0]}: {e}")
                    failed += 1
                    continue
                for item_id in chunk:
                    try:
                        self._make_request(
                            method,
                            f"/emby/Collections/{collection_id}/Items",
                            params={"Ids": item_id},
                            data=None,
                        )
                        succeeded += 1
                    except Exception as item_error:
                        logger.error(f"合集成员变更失败 {method} {item_id}: {item_error}")
                        failed += 1
        return succeeded, failed

    def get_item_image_url(self, item_id: str, image_tag: str = None, size: str = "w500") -> str:
        if not item_id:
            return None
        width = size.split("w")[-1]
        poster_url = f"{self.emby_host}/Items/{item_id}/Images/Primary?maxWidth={width}"
        if image_tag:
            poster_url += f"&tag={image_tag}"
        return poster_url

    def mark_as_played(self, item_id, user_id=None):
        """Mark an item as played
        Args:
            item_id (str): ID of the item to mark
            user_id (str, optional): User ID, uses configured user if None
        """
        if not user_id:
            user_id = self.get_users().get(self.emby_user)
        return self._make_request('post', f'/emby/Users/{user_id}/PlayedItems/{item_id}')

    def mark_as_unplayed(self, item_id, user_id=None):
        """Mark an item as unplayed
        """
        if not user_id:
            user_id = self.emby_user_id
        return self._make_request('delete', f'/emby/Users/{user_id}/PlayedItems/{item_id}')

    def mark_as_favorite(self, item_id, user_id=None):
        """Mark an item as favorite
        Args:
            item_id (str): ID of the item to mark
            user_id (str, optional): User ID, uses configured user if None
        """
        if not user_id:
            user_id = self.emby_user_id
        return self._make_request('post', f'/emby/Users/{user_id}/FavoriteItems/{item_id}')

    def unmark_as_favorite(self, item_id, user_id=None):
        """Remove an item from favorites
        Args:
            item_id (str): ID of the item to unmark
            user_id (str, optional): User ID, uses configured user if None
        """
        if not user_id:
            user_id = self.emby_user_id
        return self._make_request('delete', f'/emby/Users/{user_id}/FavoriteItems/{item_id}')

    def update_playback_position(self, item_id, position_ticks, user_id=None):
        """Update playback position for an item
        """
        if not user_id:
            user_id = self.emby_user_id
        data = {
            "PlaybackPositionTicks": position_ticks
        }
        return self._make_request('post', f'/emby/Users/{user_id}/Items/{item_id}/UserData', data=data)

    def get_poster_url(self, title: str, imdb_id: str = None, tmdb_id: int = None, size: str = "w500") -> str:
        """从 Emby 获取海报地址。优先按 IMDb/TMDB 匹配电影或剧，再按标题回退。"""
        try:
            params = {
                "Recursive": True,
                "Fields": "ProviderIds,ImageTags",
                "SearchTerm": title,
                "IncludeItemTypes": "Movie,Series",
            }
            response = self._make_request('get', '/emby/Items', params=params)
            items = response.get("Items", []) if isinstance(response, dict) else []
            if not items:
                logger.error(f"No items found for title: {title}")
                return None

            tmdb_str = str(tmdb_id) if tmdb_id else ""
            matched_item = None
            if imdb_id or tmdb_str:
                for item in items:
                    provider_ids = item.get("ProviderIds") or {}
                    if (imdb_id and provider_ids.get("Imdb") == imdb_id) or \
                       (tmdb_str and str(provider_ids.get("Tmdb") or "") == tmdb_str):
                        matched_item = item
                        break

            if not matched_item and title:
                title_lower = title.strip().lower()
                for item in items:
                    if (item.get("Name") or "").strip().lower() == title_lower:
                        matched_item = item
                        break

            if not matched_item:
                matched_item = next(
                    (item for item in items if item.get("Type") == "Series"),
                    items[0],
                )

            item_id = matched_item.get("Id")
            if not item_id:
                return None
            width = size.split("w")[-1]
            poster_url = f"{self.emby_host}/Items/{item_id}/Images/Primary?maxWidth={width}"
            image_tag = (matched_item.get("ImageTags") or {}).get("Primary")
            if image_tag:
                poster_url += f"&tag={image_tag}"
            return poster_url
        except Exception as e:
            logger.error(f"Error fetching Emby data: {str(e)}")
            return None

    def to_remote_item(self, raw: Optional[dict]) -> Optional[RemoteItem]:
        if not isinstance(raw, dict) or not raw.get("Id"):
            return None
        emby_type = raw.get("Type") or ""
        item_type = _EMBY_TYPE_MAP.get(emby_type, emby_type.lower() or ITEM_MOVIE)
        season = -1
        episode = -1
        if item_type == ITEM_EPISODE:
            season = _as_int(raw.get("ParentIndexNumber"))
            episode = _as_int(raw.get("IndexNumber"))
        elif item_type == ITEM_SEASON:
            season = _as_int(raw.get("IndexNumber"))
        providers = raw.get("ProviderIds") or {}
        provider_ids = {}
        if providers.get("Imdb"):
            provider_ids["imdb"] = providers.get("Imdb")
        if providers.get("Tmdb"):
            provider_ids["tmdb"] = str(providers.get("Tmdb"))
        if providers.get("Tvdb"):
            provider_ids["tvdb"] = providers.get("Tvdb")
        series_remote_id = raw.get("SeriesId")
        if item_type == ITEM_SERIES:
            series_remote_id = raw.get("Id") or series_remote_id
        user_data = raw.get("UserData") if isinstance(raw.get("UserData"), dict) else {}
        duration = _ticks_to_seconds(raw.get("RunTimeTicks"))
        played = bool(user_data.get("Played", False))
        position_seconds = _ticks_to_seconds(user_data.get("PlaybackPositionTicks") or 0)
        play_progress = 100.0 if played else 0.0
        if position_seconds > 0 and duration > 0:
            play_progress = min(100.0, (position_seconds / duration) * 100)
        child_count = raw.get("ChildCount")
        if child_count is None:
            child_count = raw.get("RecursiveItemCount") or 0
        return RemoteItem(
            source=SOURCE_EMBY,
            remote_id=raw.get("Id"),
            item_type=item_type,
            title=raw.get("Name") or "",
            original_title=raw.get("OriginalTitle") or "",
            path=raw.get("Path"),
            provider_ids=provider_ids,
            season=season,
            episode=episode,
            series_remote_id=series_remote_id,
            series_name=(raw.get("SeriesName") or "").strip(),
            watch=WatchState(
                played=played,
                favorite=bool(user_data.get("IsFavorite", False)),
                play_count=user_data.get("PlayCount") or 1,
                position_seconds=position_seconds,
                duration_seconds=duration,
                play_progress=play_progress,
            ),
            image_tag=(raw.get("ImageTags") or {}).get("Primary"),
            child_count=int(child_count or 0),
            is_folder=bool(raw.get("IsFolder")),
        )

    def list_user_items(self) -> List[RemoteItem]:
        libraries = self.get_user_all_items() or {}
        items: List[RemoteItem] = []
        for library_items in libraries.values():
            for raw in (
                library_items.get("series", [])
                + library_items.get("movies", [])
                + library_items.get("episodes", [])
                + library_items.get("seasons", [])
            ):
                remote = self.to_remote_item(raw)
                if remote:
                    items.append(remote)
        return items

    def get_item(self, item_id: str) -> Optional[RemoteItem]:
        return self.to_remote_item(self.get_item_details(item_id))

    def get_user_item(self, item_id: str) -> Optional[RemoteItem]:
        return self.to_remote_item(self.get_user_item_details(item_id))

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
        include = ",".join(
            _TYPE_TO_EMBY.get(item_type, item_type) for item_type in item_types
        ) or "Movie,Episode,Series"
        provider = None
        if imdb_id:
            provider = f"Imdb.{imdb_id}"
        elif tmdb_id:
            provider = f"Tmdb.{tmdb_id}"
        elif tvdb_id:
            provider = f"Tvdb.{tvdb_id}"
        raw_items = self._query_raw_items(
            include,
            search_term=search_term,
            provider_id_equals=provider,
            parent_id=parent_id,
            limit=limit,
        )
        return [item for item in (self.to_remote_item(raw) for raw in raw_items) if item]

    def search_collections(self, search: str = "", limit: int = 50) -> List[CollectionRef]:
        refs = []
        for raw in self.search_boxsets(search, limit=limit):
            remote = self.to_remote_item(raw)
            if not remote:
                continue
            refs.append(
                CollectionRef(
                    remote_id=remote.remote_id,
                    name=remote.title,
                    child_count=remote.child_count,
                    image_tag=remote.image_tag,
                )
            )
        return refs

    def get_collection_items(self, collection_id: str) -> List[RemoteItem]:
        return [
            item for item in (
                self.to_remote_item(raw) for raw in self.get_boxset_items(collection_id)
            ) if item
        ]

    def parse_webhook(self, payload: dict) -> WebhookEvent:
        if not isinstance(payload, dict):
            return WebhookEvent(kind=WEBHOOK_IGNORED)
        event = str(payload.get("Event") or payload.get("event") or "").strip().lower()
        user_name = (payload.get("User") or {}).get("Name") or ""
        if event == "system.webhooktest":
            return WebhookEvent(kind=WEBHOOK_TEST, user_name=user_name, raw_event=event)
        if event == "item.rate":
            kind = WEBHOOK_FAVORITE
        elif event == "item.markunplayed":
            kind = WEBHOOK_UNPLAYED
        elif event in _WEBHOOK_WATCH_EVENTS:
            kind = WEBHOOK_WATCH
        elif event in _WEBHOOK_LIBRARY_EVENTS:
            kind = WEBHOOK_LIBRARY_NEW
        else:
            return WebhookEvent(kind=WEBHOOK_IGNORED, user_name=user_name, raw_event=event)

        raw_items = []
        raw_item = payload.get("Item") or payload.get("item")
        if isinstance(raw_item, dict):
            raw_items.append(raw_item)
        extra = payload.get("Items") or payload.get("items")
        if isinstance(extra, list):
            raw_items.extend(item for item in extra if isinstance(item, dict))
        raw_items = [item for item in raw_items if item.get("Id")]

        playback_info = payload.get("PlaybackInfo") or {}
        played_to_completion = bool(playback_info.get("PlayedToCompletion"))
        items: List[RemoteItem] = []
        for raw in raw_items:
            merged = self._enrich_raw_item(raw)
            if kind == WEBHOOK_FAVORITE:
                details = self.get_user_item_details(raw.get("Id"))
                if isinstance(details, dict) and isinstance(details.get("UserData"), dict):
                    merged = {**details, **merged}
                    merged["UserData"] = details["UserData"]
            elif kind == WEBHOOK_UNPLAYED:
                user_data = dict(merged.get("UserData") or {})
                user_data["Played"] = False
                merged["UserData"] = user_data
            elif kind == WEBHOOK_WATCH:
                user_data = dict(merged.get("UserData") or {})
                if event == "item.markplayed" or played_to_completion:
                    user_data["Played"] = True
                merged["UserData"] = user_data
            remote = self.to_remote_item(merged)
            if remote:
                items.append(remote)
        return WebhookEvent(kind=kind, user_name=user_name, items=items, raw_event=event)

    def _enrich_raw_item(self, item: dict) -> dict:
        needs_enrich = (
            not item.get("Path")
            or not item.get("ProviderIds")
            or (
                item.get("Type") == "Episode"
                and (
                    item.get("ParentIndexNumber") is None
                    or item.get("IndexNumber") is None
                    or not item.get("SeriesName")
                )
            )
        )
        if not needs_enrich:
            return item
        details = self.get_item_details(item.get("Id"))
        if not isinstance(details, dict):
            return item
        merged = {**details, **item}
        for key in (
            "Path", "ProviderIds", "UserData", "SeriesName", "SeriesId",
            "ParentIndexNumber", "IndexNumber", "RunTimeTicks",
        ):
            if not merged.get(key) and details.get(key) is not None:
                merged[key] = details.get(key)
        return merged


EmbyService = EmbyClient
