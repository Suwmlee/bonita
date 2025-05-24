import os
import transmission_rpc
import logging
from typing import List, Any, Union, Optional

from bonita.utils.singleton import Singleton
from bonita.modules.download_clients.base_client import BaseDownloadClient, torrent_info

logger = logging.getLogger(__name__)


class TransmissionClient(BaseDownloadClient, metaclass=Singleton):
    """Transmission client for interacting with Transmission API"""

    def __init__(self):
        """Initialize TransmissionClient with default values"""
        self.trsession = None
        self.protocol = 'http'
        self.host = None
        self.port = None
        self.username = None
        self.password = None
        self.source_path = ""  # 容器内路径
        self.dest_path = ""    # 宿主机路径
        self.is_initialized = False
        self.fields = ["id", "name", "hashString", "downloadDir", "error", "errorString"]

    def initialize(self, url: str, username: str, password: str, source_path: str = "", dest_path: str = "") -> bool:
        """Initialize the Transmission service with connection parameters

        Args:
            url: Transmission server URL (e.g. http://localhost:9091)
            username: Transmission username
            password: Transmission password
            source_path: Path inside Docker container
            dest_path: Path on host machine

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Parse URL components
            protocol, host, port = self.url_to_components(url)
            self.protocol = protocol
            self.host = host
            self.port = port
            self.username = username
            self.password = password
            self.source_path = source_path
            self.dest_path = dest_path

            # Test connection
            result = self.login()
            if result:
                self.is_initialized = True
                logger.info(f"Transmission service initialized with host: {self.host}, port: {self.port}")
                return True
            else:
                logger.warning("Failed to connect to Transmission server")
                self.is_initialized = False
                return False
        except Exception as ex:
            logger.error(f"Error initializing Transmission service: {ex}")
            self.is_initialized = False
            return False

    def url_to_components(self, url: str) -> tuple:
        """Parse URL into protocol, host and port components"""
        pis = url.split(':')
        protocol = 'http'
        port = None

        # Extract port if available
        pp = pis[len(pis)-1]
        if pp.strip('/').isdigit():
            port = pp.strip('/')
            pis.remove(pp)

        # Extract protocol if available
        if url.startswith('http'):
            protocol = pis[0]
            pis.remove(pis[0])

        host = ''.join(pis).strip('/')

        # Default port for HTTPS
        if not port and protocol == 'https':
            port = 443

        return protocol, host, port

    def login(self) -> Optional[transmission_rpc.Client]:
        """Attempt to login to the Transmission client

        Returns:
            Optional[transmission_rpc.Client]: Client session if successful, None if failed
        """
        try:
            self.trsession = transmission_rpc.Client(host=self.host,
                                                     port=self.port,
                                                     protocol=self.protocol,
                                                     username=self.username,
                                                     password=self.password,
                                                     timeout=10)
            return self.trsession
        except Exception as ex:
            logger.error(f"Error connecting to Transmission: {ex}")
            return None

    def getTorrents(self, ids: Optional[Union[str, int, List[Union[str, int]]]] = None,
                    fields: Optional[List[str]] = None) -> List[torrent_info]:
        """Get torrents from the Transmission client

        Args:
            ids: ID list, get all if None
            fields: Fields to retrieve (optional)

        Returns:
            List[T]: List of torrent objects
        """
        if not self.trsession:
            return []
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        torrents = self.trsession.get_torrents(ids=ids, arguments=fields)
        torrents_info = []
        for torrent in torrents:
            info = torrent_info()
            info.id = torrent.id
            info.name = torrent.name
            info.hash = torrent.hashString
            info.downloadDir = torrent.download_dir
            info.error = torrent.error
            info.errorString = torrent.error_string
            torrents_info.append(info)
        return torrents_info

    def searchByName(self, name: str, cached_torrents: Optional[List[torrent_info]] = None) -> List[torrent_info]:
        """Search torrents by name

        Args:
            name: Torrent name to search for
            cached_torrents: Optional list of pre-fetched torrents to search through

        Returns:
            List[T]: List of matching torrent objects
        """
        torrents = cached_torrents if cached_torrents is not None else self.getTorrents(fields=self.fields)
        results = []
        for i in torrents:
            if i.name == name:
                results.append(i)
        return results

    def map_path(self, path: str, inverse: bool = False) -> str:
        """Maps path between Docker container and host

        Args:
            path: Original path

        Returns:
            str: Mapped path if mapping is configured, otherwise original path
        """
        if not self.source_path or not self.dest_path:
            return path
        if inverse:
            return path.replace(self.source_path, self.dest_path)
        else:
            return path.replace(self.dest_path, self.source_path)

    def searchByPathFromTorrents(self, path: str, cached_torrents: List[torrent_info]) -> List[torrent_info]:
        """搜索路径对应的种子，使用预先获取的种子列表

        Args:
            path: Path to search for
            cached_torrents: List of pre-fetched torrents to search through

        Returns:
            List[torrent_info]: List of matching torrent objects
        """
        path = self.map_path(path)
        retry = 3
        for i in range(retry):
            name = os.path.basename(path)
            tt = self.searchByName(name, cached_torrents)
            if len(tt):
                return tt
            else:
                path = os.path.dirname(path)
        return []

    def searchByPath(self, path: str, cached_torrents: Optional[List[torrent_info]] = None) -> List[torrent_info]:
        """逐级搜索种子(最多3次)

        Args:
            path: Path to search for
            cached_torrents: Optional list of pre-fetched torrents to search through

        Returns:
            List[torrent_info]: List of matching torrent objects
        """
        if cached_torrents is not None:
            return self.searchByPathFromTorrents(path, cached_torrents)
            
        path = self.map_path(path)
        retry = 3
        for i in range(retry):
            name = os.path.basename(path)
            tt = self.searchByName(name)
            if len(tt):
                return tt
            else:
                path = os.path.dirname(path)
        return []

    def deleteTorrent(self, torrent_id: Union[int, str], delete: bool = False) -> None:
        """Remove a torrent

        Args:
            torrent_id: ID of the torrent to remove
            delete: Whether to delete the torrent data (delete_file)

        Returns:
            None
        """
        if not self.trsession:
            return None
        self.trsession.remove_torrent([torrent_id], delete_data=delete)
