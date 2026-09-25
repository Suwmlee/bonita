import logging
import os
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from bonita.db.models.record import TransRecords
from bonita.modules.downloader.base_client import BaseDownloadClient, torrent_info
from bonita.modules.downloader.qbittorrent import QBittorrentClient
from bonita.modules.downloader.transmission import TransmissionClient
from bonita.services.setting_service import SettingService
from bonita.utils.filehelper import has_video_files

logger = logging.getLogger(__name__)


class DownloaderService:
    """下载器服务。已启用的客户端都会参与查种和删种。"""

    def __init__(self, session: Session):
        self.session = session
        self.setting_service = SettingService(session)
        self._clients: List[BaseDownloadClient] = []
        self._cached_torrents: Dict[BaseDownloadClient, List[torrent_info]] = {}

    def initialize(self) -> bool:
        """初始化所有已启用的下载客户端。任一连接成功即视为可用。"""
        self._clients = []
        self._cached_torrents = {}
        self._connect_transmission()
        self._connect_qbittorrent()
        return self.is_enabled()

    def _connect_transmission(self) -> None:
        settings = self.setting_service.get_transmission_settings()
        if not settings.get("enabled"):
            return
        client = TransmissionClient()
        if client.initialize(
            url=settings.get("transmission_host", ""),
            username=settings.get("transmission_username", ""),
            password=settings.get("transmission_password", ""),
            source_path=settings.get("transmission_source_path", ""),
            dest_path=settings.get("transmission_dest_path", ""),
        ):
            self._clients.append(client)

    def _connect_qbittorrent(self) -> None:
        settings = self.setting_service.get_qbittorrent_settings()
        if not settings.get("enabled"):
            return
        client = QBittorrentClient()
        if client.initialize(
            url=settings.get("qbittorrent_host", ""),
            username=settings.get("qbittorrent_username", ""),
            password=settings.get("qbittorrent_password", ""),
            source_path=settings.get("qbittorrent_source_path", ""),
            dest_path=settings.get("qbittorrent_dest_path", ""),
        ):
            self._clients.append(client)

    def is_enabled(self) -> bool:
        return bool(self._clients)

    def load_all_torrents(self) -> List[torrent_info]:
        if not self.is_enabled():
            return []

        loaded: List[torrent_info] = []
        for client in self._clients:
            if client not in self._cached_torrents:
                self._cached_torrents[client] = client.getTorrents()
                logger.info(
                    "Fetched %s torrents from %s",
                    len(self._cached_torrents[client]),
                    client.__class__.__name__,
                )
            loaded.extend(self._cached_torrents[client])
        return loaded

    def delete_torrent_by_record(
        self,
        record: TransRecords,
        check_video_files: bool = True,
    ) -> Tuple[int, int]:
        if not self.is_enabled() or not record.srcpath:
            return 0, 0

        deleted_count = 0
        skipped_count = 0
        for client in self._clients:
            torrents = client.searchByPath(
                record.srcpath,
                cached_torrents=self._cached_torrents.get(client),
            )
            for torrent in torrents:
                if check_video_files:
                    downfolder = os.path.join(torrent.downloadDir, torrent.name)
                    torrent_directory = client.map_path(downfolder, inverse=True)
                    if torrent_directory and has_video_files(torrent_directory):
                        logger.warning(
                            "Skipping deletion of torrent with video files: %s at %s",
                            torrent.name,
                            torrent_directory,
                        )
                        skipped_count += 1
                        continue

                logger.info("Deleting torrent: %s", torrent.name)
                client.deleteTorrent(torrent.id, delete=True)
                deleted_count += 1

        return deleted_count, skipped_count

    def delete_torrents_by_records(
        self,
        records: List[TransRecords],
        check_video_files: bool = True,
    ) -> Tuple[int, int]:
        if not self.is_enabled():
            logger.warning("No download client is initialized")
            return 0, 0

        self.load_all_torrents()

        total_deleted = 0
        total_skipped = 0
        for record in records:
            deleted, skipped = self.delete_torrent_by_record(record, check_video_files)
            total_deleted += deleted
            total_skipped += skipped
        return total_deleted, total_skipped
