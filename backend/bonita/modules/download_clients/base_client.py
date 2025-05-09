from abc import ABC, abstractmethod
from typing import List, Any, Union, Optional, Dict, TypeVar, Generic


class torrent_info():
    id: int
    name: str
    hash: str
    downloadDir: str
    error: int
    errorString: str


class BaseDownloadClient(ABC):
    """Base abstract class for download clients"""

    @abstractmethod
    def initialize(self, url: str, username: str, password: str) -> bool:
        """Initialize the client with connection parameters

        Args:
            url: Client server URL
            username: Client username
            password: Client password

        Returns:
            bool: True if initialization was successful
        """
        pass

    @abstractmethod
    def login(self) -> Optional[Any]:
        """Attempt to login to the client

        Returns:
            Optional[Any]: Client session if successful, None if failed
        """
        pass

    @abstractmethod
    def getTorrents(self, ids: List[int]) -> List[torrent_info]:
        """Get torrents from the client

        Args:
            ids: Torrent IDs to fetch (optional)

        Returns:
            List[torrent_file]: List of torrent objects
        """
        pass

    @abstractmethod
    def searchByName(self, name: str) -> List[torrent_info]:
        """Search torrents by name

        Args:
            name: Torrent name to search for

        Returns:
            List[torrent_file]: List of matching torrent objects
        """
        pass

    @abstractmethod
    def searchByPath(self, path: str) -> List[torrent_info]:
        """Search torrents by path

        Args:
            path: Path to search for

        Returns:
            List[torrent_file]: List of matching torrent objects
        """
        pass

    @abstractmethod
    def deleteTorrent(self, torrent_id: int, delete: bool = False) -> None:
        """Remove a torrent

        Args:
            torrent_id: ID of the torrent to remove
            delete: Whether to delete the torrent data

        Returns:
            None
        """
        pass
