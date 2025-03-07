import logging
import requests

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

        logger.debug(f"[+] emby scan: sending request to {emby_host}")

        response = requests.post(scan_url)

        if response.status_code == 204 or response.status_code == 200:
            logger.debug(f"[+] emby scan: library scan triggered successfully")
            return True
        else:
            logger.error(f"Failed to trigger Emby library scan. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Failed to trigger Emby library scan. Status code: {response.status_code}")
