import logging
from typing import List, Optional, Union

import transmission_rpc

from bonita.modules.downloader.base_client import BaseDownloadClient, torrent_info
from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class TransmissionClient(BaseDownloadClient, metaclass=Singleton):
    """Transmission client for interacting with Transmission API"""

    def __init__(self):
        """Initialize TransmissionClient with default values"""
        super().__init__()
        self.trsession = None
        self.protocol = 'http'
        self.host = None
        self.port = None
        self.username = None
        self.password = None
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
            if self.login():
                logger.info(f"Transmission service initialized with host: {self.host}, port: {self.port}")
                return True
            logger.warning("Failed to connect to Transmission server")
            return False
        except Exception as ex:
            logger.error(f"Error initializing Transmission service: {ex}")
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

    def getTorrents(self, ids: Optional[Union[str, int, List[Union[str, int]]]] = None) -> List[torrent_info]:
        """Get torrents from the Transmission client

        Args:
            ids: ID list, get all if None

        Returns:
            List[T]: List of torrent objects
        """
        if not self.trsession:
            return []
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        torrents = self.trsession.get_torrents(ids=ids, arguments=self.fields)
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
