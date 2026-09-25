import logging
from typing import List, Optional, Union

import qbittorrentapi

from bonita.modules.downloader.base_client import BaseDownloadClient, torrent_info
from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)

_ERROR_STATES = {"error", "missingFiles"}


class QBittorrentClient(BaseDownloadClient, metaclass=Singleton):
    """qBittorrent WebUI API 客户端。"""

    def __init__(self):
        super().__init__()
        self.session: Optional[qbittorrentapi.Client] = None
        self.host = ""
        self.username = ""
        self.password = ""

    def initialize(
        self,
        url: str,
        username: str,
        password: str,
        source_path: str = "",
        dest_path: str = "",
    ) -> bool:
        self.host = (url or "").strip().rstrip("/")
        self.username = username or ""
        self.password = password or ""
        self.source_path = source_path or ""
        self.dest_path = dest_path or ""
        self.session = None

        if not self.host:
            logger.warning("qBittorrent host is empty")
            return False
        if self.login():
            logger.info("qBittorrent service initialized with host: %s", self.host)
            return True

        logger.warning("Failed to connect to qBittorrent server")
        return False

    def login(self) -> Optional[qbittorrentapi.Client]:
        try:
            client = qbittorrentapi.Client(
                host=self.host,
                username=self.username,
                password=self.password,
                REQUESTS_ARGS={"timeout": 10},
            )
            client.auth_log_in()
            client.app_version()
            self.session = client
            return client
        except qbittorrentapi.LoginFailed as ex:
            logger.error("qBittorrent login failed: %s", ex)
        except Exception as ex:
            logger.error("Error connecting to qBittorrent: %s", ex)
        self.session = None
        return None

    def getTorrents(
        self,
        ids: Optional[Union[str, int, List[Union[str, int]]]] = None,
    ) -> List[torrent_info]:
        if not self.session:
            return []

        hashes = None
        if isinstance(ids, list):
            hashes = [str(item) for item in ids]
        elif ids:
            hashes = str(ids)

        try:
            torrents = self.session.torrents_info(torrent_hashes=hashes)
        except Exception as ex:
            logger.error("Error fetching qBittorrent torrents: %s", ex)
            return []

        result = []
        for torrent in torrents:
            state = torrent.state or ""
            info = torrent_info()
            info.id = torrent.hash
            info.name = torrent.name
            info.hash = torrent.hash
            info.downloadDir = torrent.save_path or ""
            info.error = 1 if state in _ERROR_STATES else 0
            info.errorString = state if info.error else ""
            result.append(info)
        return result

    def deleteTorrent(self, torrent_id: Union[int, str], delete: bool = False) -> None:
        if not self.session or not torrent_id:
            return
        self.session.torrents_delete(delete_files=delete, torrent_hashes=str(torrent_id))
