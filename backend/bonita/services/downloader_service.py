import logging
import os
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from bonita.modules.downloader.transmission import TransmissionClient
from bonita.modules.downloader.base_client import torrent_info
from bonita.db.models.record import TransRecords
from bonita.services.setting_service import SettingService
from bonita.utils.filehelper import has_video_files

logger = logging.getLogger(__name__)


class DownloaderService:
    """下载器服务，提供对下载客户端（如Transmission）的业务逻辑操作"""

    def __init__(self, session: Session):
        self.session = session
        self.setting_service = SettingService(session)
        self._transmission_client: Optional[TransmissionClient] = None
        self._cached_torrents: Optional[List[torrent_info]] = None
        self._is_enabled = False

    def initialize_transmission(self) -> bool:
        """初始化 Transmission 客户端

        Returns:
            bool: 是否成功初始化
        """
        transmission_settings = self.setting_service.get_transmission_settings()

        if not transmission_settings.get("enabled"):
            logger.warning("Transmission is not enabled")
            self._is_enabled = False
            return False

        if not self._transmission_client:
            self._transmission_client = TransmissionClient()

        transmission_url = transmission_settings.get("transmission_host", "")
        transmission_username = transmission_settings.get("transmission_username", "")
        transmission_password = transmission_settings.get("transmission_password", "")
        transmission_source_path = transmission_settings.get("transmission_source_path", "")
        transmission_dest_path = transmission_settings.get("transmission_dest_path", "")

        success = self._transmission_client.initialize(
            url=transmission_url,
            username=transmission_username,
            password=transmission_password,
            source_path=transmission_source_path,
            dest_path=transmission_dest_path
        )

        self._is_enabled = success
        return success

    def is_enabled(self) -> bool:
        """检查下载器是否已启用并初始化

        Returns:
            bool: 是否已启用
        """
        return self._is_enabled and self._transmission_client is not None

    def load_all_torrents(self) -> List[torrent_info]:
        """加载所有种子信息并缓存

        Returns:
            List[torrent_info]: 种子信息列表
        """
        if not self.is_enabled():
            return []

        if self._cached_torrents is None:
            self._cached_torrents = self._transmission_client.getTorrents(
                fields=self._transmission_client.fields
            )
            logger.info(f"Fetched {len(self._cached_torrents)} torrents from Transmission")

        return self._cached_torrents

    def clear_cache(self) -> None:
        """清除缓存的种子信息"""
        self._cached_torrents = None

    def delete_torrent_by_record(
        self,
        record: TransRecords,
        check_video_files: bool = True
    ) -> Tuple[int, int]:
        """根据转移记录删除对应的种子

        Args:
            record: 转移记录
            check_video_files: 是否检查视频文件存在（如果存在则跳过删除）

        Returns:
            Tuple[int, int]: (删除的种子数, 跳过的种子数)
        """
        if not self.is_enabled():
            logger.warning("Transmission client is not initialized")
            return 0, 0

        if not record.srcpath:
            return 0, 0

        # 查找对应的种子
        torrents = self._transmission_client.searchByPath(
            record.srcpath,
            cached_torrents=self._cached_torrents
        )

        if not torrents:
            return 0, 0

        deleted_count = 0
        skipped_count = 0

        for torrent in torrents:
            # 检查种子目录是否还存在视频文件
            if check_video_files:
                downfolder = os.path.join(torrent.downloadDir, torrent.name)
                torrent_directory = self._transmission_client.map_path(downfolder, inverse=True)

                if torrent_directory and has_video_files(torrent_directory):
                    logger.warning(
                        f"Skipping deletion of torrent with video files: {torrent.name} at {torrent_directory}"
                    )
                    skipped_count += 1
                    continue

            logger.info(f"Deleting torrent: {torrent.name}")
            self._transmission_client.deleteTorrent(torrent.id, delete=True)
            deleted_count += 1

        return deleted_count, skipped_count

    def delete_torrents_by_records(
        self,
        records: List[TransRecords],
        check_video_files: bool = True
    ) -> Tuple[int, int]:
        """批量删除记录对应的种子

        Args:
            records: 转移记录列表
            check_video_files: 是否检查视频文件存在（如果存在则跳过删除）

        Returns:
            Tuple[int, int]: (删除的种子数, 跳过的种子数)
        """
        if not self.is_enabled():
            logger.warning("Transmission client is not initialized")
            return 0, 0

        # 预加载所有种子
        self.load_all_torrents()

        total_deleted = 0
        total_skipped = 0

        for record in records:
            deleted, skipped = self.delete_torrent_by_record(record, check_video_files)
            total_deleted += deleted
            total_skipped += skipped

        return total_deleted, total_skipped

    def get_client(self) -> Optional[TransmissionClient]:
        """获取 Transmission 客户端实例

        Returns:
            Optional[TransmissionClient]: 客户端实例
        """
        return self._transmission_client if self.is_enabled() else None
