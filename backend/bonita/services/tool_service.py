import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from bonita import schemas
from bonita.celery_tasks.tasks import celery_import_nfo
from bonita.modules.media_service.sync import sync_emby_history
from bonita.services.record_service import RecordService
from bonita.services.setting_service import SettingService
from bonita.modules.download_clients.transmission import TransmissionClient
from bonita.utils.filehelper import has_video_files

logger = logging.getLogger(__name__)


class ToolService:
    """工具服务，提供各种系统工具和操作的业务逻辑"""

    def __init__(self, session: Session):
        self.session = session
        self.record_service = RecordService(session)
        self.setting_service = SettingService(session)

    def import_nfo(self, folder_path: str, option: str) -> schemas.TaskStatus:
        """导入NFO信息

        Args:
            folder_path: NFO文件所在文件夹路径
            option: 导入选项

        Returns:
            schemas.TaskStatus: 任务状态
        """
        logger.info(f"Run import nfo: {folder_path}")
        if folder_path and option:
            task = celery_import_nfo.delay(folder_path, option)
            return schemas.TaskStatus(
                id=task.id,
                name="import nfo",
                status='ACTIVE'
            )
        else:
            return schemas.TaskStatus(
                id=None,
                name="import nfo",
                status='FAILED'
            )

    def emby_scan(self, folder_args: schemas.ToolArgsParam) -> schemas.TaskStatus:
        """扫描Emby

        Args:
            folder_args: 工具参数

        Returns:
            schemas.TaskStatus: 任务状态
        """
        logger.info("Run emby scan")
        # 目前这个功能尚未实现，返回失败状态
        return schemas.TaskStatus(
            id=None,
            name="emby scan",
            status='FAILED'
        )

    def sync_emby_watch_history(self) -> schemas.Response:
        """同步Emby观看历史

        Returns:
            schemas.Response: 操作响应
        """
        logger.info("Sync emby watch history")
        sync_emby_history(self.session)

        return schemas.Response(
            success=True,
            message="sync emby watch history success"
        )

    def cleanup_data(self, delete_files: bool) -> schemas.Response:
        """清理下载器、转移记录和实际文件

        Args:
            delete_files: 是否删除文件

        Returns:
            schemas.Response: 操作响应
        """
        logger.info("Check and cleanup data")

        # 获取需要清理的记录（deadtime已过期或srcdeleted标记的记录）
        current_time = datetime.now()
        
        # 直接从数据库获取需要清理的记录
        records_to_cleanup = self.record_service.get_records_to_cleanup(current_time)

        logger.info(f"Found {len(records_to_cleanup)} records to cleanup")

        # 如果没有需要清理的记录，直接返回成功
        if not records_to_cleanup:
            return schemas.Response(
                success=True,
                message="No records need to be cleaned up"
            )

        # 初始化Transmission客户端
        transmission_client = TransmissionClient()
        transmission_settings = self.setting_service.get_transmission_settings()

        if transmission_settings.get("enabled"):
            # 初始化Transmission客户端
            transmission_url = transmission_settings.get("transmission_host", "")
            transmission_username = transmission_settings.get("transmission_username", "")
            transmission_password = transmission_settings.get("transmission_password", "")
            transmission_source_path = transmission_settings.get("transmission_source_path", "")
            transmission_dest_path = transmission_settings.get("transmission_dest_path", "")

            transmission_client.initialize(
                url=transmission_url,
                username=transmission_username,
                password=transmission_password,
                source_path=transmission_source_path,
                dest_path=transmission_dest_path
            )
        else:
            logger.warning("Transmission is not enabled, skipping torrent cleanup")

        # 统计信息
        deleted_count = 0
        skipped_count = 0

        # 处理每条记录
        for record in records_to_cleanup:
            try:
                # 查找对应的种子
                if transmission_settings.get("enabled") and record.srcpath:
                    torrents = transmission_client.searchByPath(record.srcpath)

                    # 如果找到匹配的种子且需要删除种子文件
                    if torrents and delete_files:
                        for torrent in torrents:
                            # 检查种子目录是否还存在视频文件
                            torrent_directory = torrent.downloadDir
                            if torrent_directory and has_video_files(torrent_directory):
                                logger.warning(f"Skipping deletion of torrent with video files: {torrent.name} at {torrent_directory}")
                                skipped_count += 1
                                continue
                            logger.info(f"Deleting torrent: {torrent.name}")
                            transmission_client.deleteTorrent(torrent.id, delete=True)
                            deleted_count += 1
                    # 如果找到匹配的种子但不需要删除文件，只记录日志
                    elif torrents:
                        for torrent in torrents:
                            logger.info(f"Found matching torrent: {torrent.name} (not deleting)")
            except Exception as e:
                logger.error(f"Error processing record {record.id}: {str(e)}")

        return schemas.Response(
            success=True,
            message=f"Cleanup completed. Deleted {deleted_count} torrents, skipped {skipped_count} torrents with video files."
        )
