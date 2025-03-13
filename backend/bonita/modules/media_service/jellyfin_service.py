import logging
import requests
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class JellyfinService:
    """Jellyfin media server service for interacting with Jellyfin API"""
    
    @staticmethod
    def trigger_library_scan(jellyfin_host, jellyfin_apikey, jellyfin_userid=None):
        """Triggers a library scan in Jellyfin

        Args:
            jellyfin_host (str): The Jellyfin server host URL
            jellyfin_apikey (str): The Jellyfin API key
            jellyfin_userid (str, optional): The Jellyfin user ID

        Returns:
            bool: True if scan was triggered successfully, False otherwise
        """
        if not jellyfin_host or not jellyfin_apikey:
            raise Exception("Jellyfin host or API key not configured")

        # Remove trailing slash if present
        if jellyfin_host.endswith('/'):
            jellyfin_host = jellyfin_host[:-1]

        # Construct the URL for the Jellyfin library scan endpoint
        scan_url = f"{jellyfin_host}/Library/Refresh"

        headers = {
            "X-Emby-Token": jellyfin_apikey
        }

        logger.info(f"[+] jellyfin scan: sending request to {jellyfin_host}")

        response = requests.post(scan_url, headers=headers)

        if response.status_code == 204 or response.status_code == 200:
            logger.info(f"[+] jellyfin scan: library scan triggered successfully")
            return True
        else:
            logger.error(f"Failed to trigger Jellyfin library scan. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to trigger Jellyfin library scan. Status code: {response.status_code}")
    
    @staticmethod
    def get_watch_history(jellyfin_host, jellyfin_apikey, jellyfin_userid=None, days=30, limit=100):
        """Fetches watch history from Jellyfin

        Args:
            jellyfin_host (str): The Jellyfin server host URL
            jellyfin_apikey (str): The Jellyfin API key
            jellyfin_userid (str, optional): The Jellyfin user ID
            days (int): Number of days of history to fetch
            limit (int): Maximum number of items to fetch

        Returns:
            list: List of watched items with metadata
        """
        if not jellyfin_host or not jellyfin_apikey:
            raise Exception("Jellyfin host or API key not configured")

        # Remove trailing slash if present
        if jellyfin_host.endswith('/'):
            jellyfin_host = jellyfin_host[:-1]
            
        # Calculate start date based on days parameter (milliseconds since epoch)
        start_date = int((time.time() - (days * 24 * 60 * 60)) * 1000)
        
        headers = {
            "X-Emby-Token": jellyfin_apikey
        }

        # If user ID is provided, use it to fetch user-specific data
        # Otherwise, fetch all available data
        if jellyfin_userid:
            history_url = f"{jellyfin_host}/Users/{jellyfin_userid}/Items/Resume"
        else:
            # First get the active user's ID
            user_url = f"{jellyfin_host}/Users"
            try:
                user_response = requests.get(user_url, headers=headers)
                if user_response.status_code == 200:
                    users = user_response.json()
                    if users and len(users) > 0:
                        # Use the first user
                        jellyfin_userid = users[0].get("Id")
                        history_url = f"{jellyfin_host}/Users/{jellyfin_userid}/Items/Resume"
                    else:
                        raise Exception("No users found in Jellyfin")
                else:
                    raise Exception(f"Failed to get Jellyfin users. Status code: {user_response.status_code}")
            except Exception as e:
                logger.error(f"Error getting Jellyfin users: {str(e)}")
                raise
        
        params = {
            "Limit": limit,
            "StartIndex": 0,
            "IncludeItemTypes": "Movie,Episode",
            "Recursive": "true",
            "Fields": "Overview,Genres,MediaSources,Path,ProviderIds,DateCreated",
            "EnableTotalRecordCount": "false",
            "MediaTypes": "Video"
        }

        try:
            logger.info(f"[+] Fetching Jellyfin watch history: sending request to {jellyfin_host}")
            response = requests.get(history_url, headers=headers, params=params)
            
            if response.status_code == 200:
                history_data = response.json()
                items = history_data.get("Items", [])
                logger.info(f"[+] Successfully fetched {len(items)} watched items from Jellyfin")
                return items
            else:
                logger.error(f"Failed to fetch Jellyfin watch history. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Failed to fetch Jellyfin watch history. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during Jellyfin API request: {str(e)}")
            raise
    
    @staticmethod
    def get_item_details(jellyfin_host, jellyfin_apikey, item_id, jellyfin_userid=None):
        """Fetches details for a specific item from Jellyfin

        Args:
            jellyfin_host (str): The Jellyfin server host URL
            jellyfin_apikey (str): The Jellyfin API key
            item_id (str): ID of the item to fetch details for
            jellyfin_userid (str, optional): The Jellyfin user ID

        Returns:
            dict: Item details
        """
        if not jellyfin_host or not jellyfin_apikey or not item_id:
            return None

        # Remove trailing slash if present
        if jellyfin_host.endswith('/'):
            jellyfin_host = jellyfin_host[:-1]
        
        headers = {
            "X-Emby-Token": jellyfin_apikey
        }
        
        # Construct the URL for the item details endpoint
        details_url = f"{jellyfin_host}/Items/{item_id}"
        params = {
            "Fields": "Overview,Genres,MediaSources,Path,ProviderIds,DateCreated"
        }
        
        if jellyfin_userid:
            params["UserId"] = jellyfin_userid

        try:
            response = requests.get(details_url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch Jellyfin item details. Status code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching Jellyfin item details: {str(e)}")
            return None 