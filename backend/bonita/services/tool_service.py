import logging
import uuid
from sqlalchemy.orm import Session

from bonita import schemas
from bonita.celery_tasks.tasks import celery_import_nfo
from bonita.modules.media_service.sync import sync_emby_history
from bonita.services.record_service import RecordService
from bonita.services.setting_service import SettingService
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

        # 提取记录ID列表
        record_ids = [record.id for record in records_to_cleanup]

        # 删除记录（force=True 会自动删除种子）
        try:
            success, message, _, _ = self.record_service.delete_records(record_ids, force=True)
            return schemas.Response(
                success=success,
                message=f"Cleanup completed. {message}"
            )
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return schemas.Response(
                success=False,
                message=f"Cleanup failed: {str(e)}"
            )
