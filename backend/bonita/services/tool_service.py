import logging
import os
import uuid
from sqlalchemy.orm import Session

from bonita import schemas
from bonita.celery_tasks.tasks import celery_import_nfo
from bonita.modules.media_service.sync import sync_emby_history
from bonita.services.record_service import RecordService
from bonita.services.setting_service import SettingService
from bonita.modules.download_clients.transmission import TransmissionClient
from bonita.utils.filehelper import has_video_files
from bonita.core.enums import TaskStatusEnum

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
                task_id=task.id,
                name="import nfo",
                status=TaskStatusEnum.PENDING,
                task_type='ImportNFO',
                progress=0.0,
                step='任务已启动'
            )
        else:
            return schemas.TaskStatus(
                task_id=str(uuid.uuid4()),
                name="import nfo",
                status=TaskStatusEnum.FAILURE,
                task_type='ImportNFO',
                progress=0.0,
                step='参数错误',
                error_message='缺少必要参数'
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
            task_id=str(uuid.uuid4()),
            name="emby scan",
            status=TaskStatusEnum.FAILURE,
            task_type='EmbyScan',
            progress=0.0,
            step='功能未实现',
            error_message='该功能尚未实现'
        )

    def sync_emby_watch_history(self, force: bool = False) -> schemas.Response:
        """同步Emby观看历史

        Args:
            force: 是否强制覆盖本地数据（包括喜爱标记），默认为False

        Returns:
            schemas.Response: 操作响应
        """
        logger.info(f"Sync emby watch history, force={force}")
        sync_emby_history(self.session, force=force)

        return schemas.Response(
            success=True,
            message=f"sync emby watch history success (force={'enabled' if force else 'disabled'})"
        )

    def cleanup_data(self, force_flag: bool) -> schemas.Response:
        """清理下载器、转移记录和实际文件

        Args:
            force_flag: 是否强制删除文件

        Returns:
            schemas.Response: 操作响应
        """
        logger.info("Check and cleanup data")
        records_to_cleanup = self.record_service.get_records_to_cleanup(force_flag)
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
        all_torrents = []
        
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
            
            # 预先获取所有种子，避免重复查询
            all_torrents = transmission_client.getTorrents(fields=transmission_client.fields)
            logger.info(f"Fetched {len(all_torrents)} torrents from Transmission")
        else:
            logger.warning("Transmission is not enabled, skipping torrent cleanup")

        # 统计信息
        deleted_count = 0
        skipped_count = 0
        # 处理每条记录
        for record in records_to_cleanup:
            try:
                self.record_service.delete_records([record.id], True)
                # 查找对应的种子
                if transmission_settings.get("enabled") and record.srcpath:
                    torrents = transmission_client.searchByPath(record.srcpath, cached_torrents=all_torrents)
                    # 如果找到匹配的种子且需要删除种子文件
                    if torrents:
                        for torrent in torrents:
                            # 检查种子目录是否还存在视频文件
                            downfolder = os.path.join(torrent.downloadDir, torrent.name)
                            torrent_directory = transmission_client.map_path(downfolder, inverse=True)
                            if torrent_directory and has_video_files(torrent_directory):
                                logger.warning(
                                    f"Skipping deletion of torrent with video files: {torrent.name} at {torrent_directory}")
                                skipped_count += 1
                                continue
                            logger.info(f"Deleting torrent: {torrent.name}")
                            transmission_client.deleteTorrent(torrent.id, delete=True)
                            deleted_count += 1
            except Exception as e:
                logger.error(f"Error processing record {record.id}: {str(e)}")

        return schemas.Response(
            success=True,
            message=f"Cleanup completed. Deleted {deleted_count} torrents, skipped {skipped_count} torrents with video files."
        )
