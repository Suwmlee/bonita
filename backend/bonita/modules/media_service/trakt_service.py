import logging
import requests
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class TraktService:
    """Trakt service for interacting with Trakt API"""
    
    BASE_URL = "https://api.trakt.tv"
    API_VERSION = "2"
    
    @staticmethod
    def get_watch_history(client_id, access_token, days=30, limit=100, extended=False):
        """Fetches watch history for movies from Trakt
        
        Args:
            client_id (str): Trakt API client ID
            access_token (str): Trakt API access token
            days (int): Number of days of history to fetch
            limit (int): Maximum number of items to fetch
            extended (bool): Whether to fetch extended info
            
        Returns:
            list: List of watched movies with metadata
        """
        if not client_id or not access_token:
            raise Exception("Trakt client ID or access token not configured")
            
        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": TraktService.API_VERSION,
            "trakt-api-key": client_id,
            "Authorization": f"Bearer {access_token}"
        }
        
        # Construct URL for watched movies
        endpoint = f"{TraktService.BASE_URL}/sync/history/movies"
        params = {"limit": limit}
        
        if extended:
            params["extended"] = "full"
            
        try:
            logger.info(f"[+] Fetching Trakt watch history: sending request")
            response = requests.get(endpoint, headers=headers, params=params)
            
            if response.status_code == 200:
                watched_movies = response.json()
                logger.info(f"[+] Successfully fetched {len(watched_movies)} watched movies from Trakt")
                return watched_movies
            else:
                logger.error(f"Failed to fetch Trakt watch history. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Failed to fetch Trakt watch history. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during Trakt API request: {str(e)}")
            raise
            
    @staticmethod
    def get_ratings(client_id, access_token, type="movies"):
        """Fetches ratings for movies from Trakt
        
        Args:
            client_id (str): Trakt API client ID
            access_token (str): Trakt API access token
            type (str): Content type to fetch (movies, shows, etc.)
            
        Returns:
            dict: Dictionary mapping trakt_id to rating
        """
        if not client_id or not access_token:
            raise Exception("Trakt client ID or access token not configured")
            
        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": TraktService.API_VERSION,
            "trakt-api-key": client_id,
            "Authorization": f"Bearer {access_token}"
        }
        
        # Construct URL for ratings
        endpoint = f"{TraktService.BASE_URL}/sync/ratings/{type}"
        
        try:
            logger.info(f"[+] Fetching Trakt ratings: sending request")
            response = requests.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                ratings_data = response.json()
                
                # Create a mapping of trakt_id to rating
                ratings_map = {}
                for item in ratings_data:
                    if "movie" in item:
                        movie = item["movie"]
                        trakt_id = str(movie["ids"]["trakt"])
                        rating = item["rating"]
                        ratings_map[trakt_id] = rating
                
                logger.info(f"[+] Successfully fetched ratings for {len(ratings_map)} movies from Trakt")
                return ratings_map
            else:
                logger.error(f"Failed to fetch Trakt ratings. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Failed to fetch Trakt ratings. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during Trakt API request: {str(e)}")
            raise 