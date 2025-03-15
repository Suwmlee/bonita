import logging
import requests
from typing import Any, Dict, List, Optional, Union

from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class EmbyService(metaclass=Singleton):
    """Emby media server service for interacting with Emby API"""

    def initialize(self, emby_host: str, emby_apikey: str, emby_user: str = None):
        """Initialize the Emby service with connection parameters
        """
        self.emby_host = emby_host.rstrip('/') if emby_host else None
        self.emby_apikey = emby_apikey
        self.headers = {
            "X-Emby-Token": self.emby_apikey,
            "Content-Type": "application/json"
        }
        if not self.emby_host or not self.emby_apikey:
            logger.warning("Emby service initialized with missing host or API key")
            return False
        try:
            self.emby_user = emby_user.lower()
            if self.emby_user:
                self.emby_user_id = self.get_users().get(self.emby_user)
        except Exception as e:
            logger.error(f"Error initializing Emby service: {e}")
            return False
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
            logger.info(f"[+] Emby request: {method.upper()} {url}")
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

    def get_library_user_watched(self, library_id: str, library_type: str, user_id: str) -> dict[str, Any]:
        """Get watched items for a library
        """
        if not library_id or not user_id:
            return None

        result = {
            "movies": [],
            "episodes": []
        }

        # Get watched movies
        if library_type == "movies" or not library_type:
            # Get fully watched movies
            watched_movies = self._make_request(
                'get',
                f'/Users/{user_id}/Items',
                params={
                    "ParentId": library_id,
                    "Filters": "IsPlayed",
                    "IncludeItemTypes": "Movie",
                    "Recursive": "True",
                    "Fields": "ItemCounts,ProviderIds,MediaSources"
                }
            )

            if isinstance(watched_movies, dict) and watched_movies.get("Items"):
                result["movies"].extend(watched_movies.get("Items", []))

            # Get in-progress movies
            in_progress_movies = self._make_request(
                'get',
                f'/Users/{user_id}/Items',
                params={
                    "ParentId": library_id,
                    "Filters": "IsResumable",
                    "IncludeItemTypes": "Movie",
                    "Recursive": "True",
                    "Fields": "ItemCounts,ProviderIds,MediaSources"
                }
            )

            if isinstance(in_progress_movies, dict) and in_progress_movies.get("Items"):
                result["movies"].extend(in_progress_movies.get("Items", []))

        # Get watched TV shows and episodes
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
                # Filter to shows that have been at least partially watched
                watched_shows = []
                for show in all_shows.get("Items", []):
                    if show.get("UserData", {}).get("PlayedPercentage", 0) > 0:
                        watched_shows.append(show)

                # For each watched show, get its episodes
                for show in watched_shows:
                    show_id = show.get("Id")
                    show_episodes = self._make_request(
                        'get',
                        f'/Shows/{show_id}/Episodes',
                        params={
                            "userId": user_id,
                            "isPlaceHolder": "false",
                            "Fields": "ProviderIds,MediaSources"
                        }
                    )

                    if isinstance(show_episodes, dict) and show_episodes.get("Items"):
                        # Add watched episodes to result
                        for episode in show_episodes.get("Items", []):
                            user_data = episode.get("UserData", {})
                            # Include if fully watched or watched more than a minute
                            if user_data.get("Played") or user_data.get("PlaybackPositionTicks", 0) > 600000000:
                                result["episodes"].append(episode)

        return result

    def get_user_watched(self, user_id=None) -> dict[str, Any]:
        """Get all watched items for a user across all libraries
        """
        if not user_id:
            user_id = self.emby_user_id
        if not user_id:
            logger.warning("No user ID available to fetch watched items")
            return None

        # Get all libraries for the user
        libraries = self.get_user_libraries(user_id)
        if not libraries:
            logger.warning("No libraries found for user")
            return None

        result = {}

        # Get watched items for each library
        for library_id, library_info in libraries.items():
            library_name = library_info.get("name")
            library_type = library_info.get("type")
            if not library_name or not library_type:
                continue

            watched_items = self.get_library_user_watched(library_id, library_type, user_id)
            if watched_items:
                result[library_id] = watched_items

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
