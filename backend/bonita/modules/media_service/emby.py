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
            logger.debug(f"[-] Emby request: {method.upper()} {url}")
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
                logger.debug(f"[+] Emby response: {response.status_code}")
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
            "episodes": []
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
                    "Fields": "ProviderIds,Path,RecursiveItemCount"
                }
            )

            if isinstance(all_shows, dict) and all_shows.get("Items"):
                # Filter to shows that have been at least partially
                matched_shows = []
                for show in all_shows.get("Items", []):
                    matched_shows.append(show)

                # For each show, get its episodes
                for show in matched_shows:
                    show_id = show.get("Id")
                    show_episodes = self._make_request(
                        'get',
                        f'/Shows/{show_id}/Episodes',
                        params={
                            "userId": user_id,
                            "isPlaceHolder": "false",
                            "Fields": "ProviderIds,Path,DateCreated,UserDataLastPlayedDate"
                        }
                    )

                    if isinstance(show_episodes, dict) and show_episodes.get("Items"):
                        # Add episodes to result
                        for episode in show_episodes.get("Items", []):
                            result["episodes"].append(episode)

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
            user_id = self.get_user_id()
        return self._make_request('delete', f'/emby/Users/{user_id}/PlayedItems/{item_id}')

    def update_playback_position(self, item_id, position_ticks, user_id=None):
        """Update playback position for an item
        """
        if not user_id:
            user_id = self.get_user_id()
        data = {
            "PlaybackPositionTicks": position_ticks
        }
        return self._make_request('post', f'/emby/Users/{user_id}/Items/{item_id}/UserData', data=data)

    def get_poster_url(self, title: str, imdb_id: str = None, tmdb_id: int = None, size: str = "w500") -> str:
        """ 从 Emby 获取海报地址
        """
        try:
            # 如果提供了 IMDb ID 或 TMDB ID，查询 Emby 中的媒体项
            search_url = "/emby/Items"
            params = {
                "Recursive": True,
                "Fields": "ProviderIds",
                "SearchTerm": title
            }
            response = self._make_request('get', search_url, params=params)
            items = response.get("Items", [])
            if not items:
                logger.error(f"No items found for title: {title}")
                return None
            matched_item = None
            # 如果提供了 IMDb 或 TMDB ID，优先查找匹配的项
            if imdb_id or tmdb_id:
                for item in items:
                    provider_ids = item.get("ProviderIds", {})
                    # 检查是否匹配 IMDb 或 TMDB ID
                    if (imdb_id and provider_ids.get("Imdb") == imdb_id) or \
                       (tmdb_id and provider_ids.get("Tmdb") == str(tmdb_id)):
                        matched_item = item
                        logger.debug(f"Found matching item with ID: {item['Id']}")
                        break
            if not matched_item:
                return None
            item_id = matched_item["Id"]
            # 获取海报图片地址
            image_url = f"{self.emby_host}/Items/{item_id}/Images/Primary?maxWidth={size.split('w')[-1]}"
            return image_url

        except Exception as e:
            logger.error(f"Error fetching Emby data: {str(e)}")
            return None
