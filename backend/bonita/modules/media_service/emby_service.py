import logging
import requests
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class EmbyService:
    """Emby media server service for interacting with Emby API"""

    @staticmethod
    def trigger_library_scan(emby_host, emby_apikey):
        """Triggers a library scan in Emby

        Args:
            emby_host (str): The Emby server host URL
            emby_apikey (str): The Emby API key

        Returns:
            bool: True if scan was triggered successfully, False otherwise
        """
        if not emby_host or not emby_apikey:
            raise Exception("Emby host or API key not configured")

        # Remove trailing slash if present
        if emby_host.endswith('/'):
            emby_host = emby_host[:-1]

        # Construct the URL for the Emby library scan endpoint
        scan_url = f"{emby_host}/Library/Refresh?api_key={emby_apikey}"

        logger.info(f"[+] emby scan: sending request to {emby_host}")

        response = requests.post(scan_url)

        if response.status_code == 204 or response.status_code == 200:
            logger.info(f"[+] emby scan: library scan triggered successfully")
            return True
        else:
            logger.error(f"Failed to trigger Emby library scan. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to trigger Emby library scan. Status code: {response.status_code}")
    
    @staticmethod
    def get_watch_history(emby_host, emby_apikey, days=30, limit=100):
        """Fetches watch history from Emby

        Args:
            emby_host (str): The Emby server host URL
            emby_apikey (str): The Emby API key
            days (int): Number of days of history to fetch
            limit (int): Maximum number of items to fetch

        Returns:
            list: List of watched items with metadata
        """
        if not emby_host or not emby_apikey:
            raise Exception("Emby host or API key not configured")

        # Remove trailing slash if present
        if emby_host.endswith('/'):
            emby_host = emby_host[:-1]

        # Calculate start date based on days parameter (milliseconds since epoch)
        start_date = int((time.time() - (days * 24 * 60 * 60)) * 1000)
        
        # Construct the URL for the Emby play history endpoint
        history_url = f"{emby_host}/emby/Users/PlayedItems"
        params = {
            "api_key": emby_apikey,
            "Limit": limit,
            "StartIndex": 0,
            "MinDate": start_date,
            "IncludeItemTypes": "Movie,Episode"
        }

        try:
            logger.info(f"[+] Fetching Emby watch history: sending request to {emby_host}")
            response = requests.get(history_url, params=params)
            
            if response.status_code == 200:
                history_data = response.json()
                items = history_data.get("Items", [])
                logger.info(f"[+] Successfully fetched {len(items)} played items from Emby")
                
                # For each item, fetch additional details
                detailed_items = []
                for item in items:
                    item_id = item.get("Id")
                    if item_id:
                        item_details = EmbyService.get_item_details(emby_host, emby_apikey, item_id)
                        if item_details:
                            # Combine play data with item details
                            item_details["DatePlayed"] = item.get("DatePlayed")
                            item_details["PlayCount"] = item.get("PlayCount", 1)
                            item_details["PlaybackPositionTicks"] = item.get("PlaybackPositionTicks", 0)
                            detailed_items.append(item_details)
                
                return detailed_items
            else:
                logger.error(f"Failed to fetch Emby watch history. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Failed to fetch Emby watch history. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during Emby API request: {str(e)}")
            raise
    
    @staticmethod
    def get_item_details(emby_host, emby_apikey, item_id):
        """Fetches details for a specific item from Emby

        Args:
            emby_host (str): The Emby server host URL
            emby_apikey (str): The Emby API key
            item_id (str): ID of the item to fetch details for

        Returns:
            dict: Item details
        """
        if not emby_host or not emby_apikey or not item_id:
            return None

        # Remove trailing slash if present
        if emby_host.endswith('/'):
            emby_host = emby_host[:-1]
        
        # Construct the URL for the item details endpoint
        details_url = f"{emby_host}/emby/Items/{item_id}"
        params = {
            "api_key": emby_apikey
        }

        try:
            response = requests.get(details_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch Emby item details. Status code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching Emby item details: {str(e)}")
            return None
