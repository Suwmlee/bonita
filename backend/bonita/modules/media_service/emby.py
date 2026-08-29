import logging
import requests
from typing import Any, Dict, List, Optional, Union

from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class EmbyService(metaclass=Singleton):
    """Emby media server service for interacting with Emby API"""

    def __init__(self):
        """Initialize EmbyService with default values"""
        self.emby_host = None
        self.emby_apikey = None
        self.emby_user = None
        self.emby_user_id = None
        self.headers = {}
        self.is_initialized = False

    def initialize(self, emby_host: str, emby_apikey: str, emby_user: str):
        """Initialize the Emby service with connection parameters
        """
        # 如果已经初始化并且参数相同，直接返回 True
        if (self.is_initialized and
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
            self.is_initialized = False
            return False
        try:
            self.emby_user = emby_user.lower()
            self.emby_user_id = self.get_users().get(self.emby_user)
            if not self.emby_user_id:
                logger.warning(f"User {self.emby_user} not found in Emby")
                self.is_initialized = False
                return False
            self.is_initialized = True
        except Exception as e:
            logger.error(f"Error initializing Emby service: {e}")
            self.is_initialized = False
            return False
        logger.info(f"Emby service initialized with host: {self.emby_host}, user: {self.emby_user}")
        return True

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
                json=data,
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
        """Fetches details for a specific item from Emby
        """
        if not item_id:
            return None
        try:
            return self._make_request('get', f'/emby/Items/{item_id}')
        except Exception as e:
            logger.error(f"Error fetching Emby item details: {str(e)}")
            return None

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
                        "ProviderIds,Path,UserData,SeriesName,SeriesId,"
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
            },
        )
        if isinstance(response, dict):
            return response.get("Items") or []
        return []

    def query_items(
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

    def add_items_to_collection(self, collection_id: str, item_ids: List[str]) -> bool:
        """把条目加入 Emby 合集。"""
        return self._mutate_collection_items("post", collection_id, item_ids)

    def remove_items_from_collection(self, collection_id: str, item_ids: List[str]) -> bool:
        """从 Emby 合集移除条目。"""
        return self._mutate_collection_items("delete", collection_id, item_ids)

    def _mutate_collection_items(self, method: str, collection_id: str, item_ids: List[str]) -> bool:
        if not collection_id or not item_ids:
            return True
        unique_ids = list(dict.fromkeys(item_ids))
        for offset in range(0, len(unique_ids), 50):
            chunk = unique_ids[offset:offset + 50]
            self._make_request(
                method,
                f"/emby/Collections/{collection_id}/Items",
                params={"Ids": ",".join(chunk)},
            )
        return True

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
