import logging
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from bonita import schemas
from bonita.tasks import (
    celery_import_nfo,
    celery_reload_scrapinglib,
    celery_sync_watch_history,
)
from bonita.services.record_service import RecordService
from bonita.services.celery_service import CeleryTaskService, TASK_WATCH_HISTORY_SYNC
from bonita.core.enums import TaskStatusEnum
from bonita.utils.http import get_active_proxy
from bonita.utils.scrapinglib_pkg import (
    fetch_latest_version,
    get_installed_version,
    is_newer,
    pip_install_upgrade,
    reload_modules,
)

logger = logging.getLogger(__name__)


class ToolService:
    """工具服务，提供各种系统工具和操作的业务逻辑"""

    def __init__(self, session: Session):
        self.session = session
        self.record_service = RecordService(session)

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

    def sync_record_path(
        self,
        old_prefix: str,
        new_prefix: str,
        task_id: Optional[int] = None
    ) -> schemas.Response:
        """批量替换转移记录的源路径前缀

        Args:
            old_prefix: 旧路径前缀
            new_prefix: 新路径前缀
            task_id: 可选，仅更新指定任务的记录

        Returns:
            schemas.Response: 操作响应
        """
        logger.info(
            f"Sync trans records path prefix: '{old_prefix}' -> '{new_prefix}', task_id={task_id}"
        )
        success, message, updated_records, updated_extrainfo = self.record_service.update_src_path_prefix(
            old_prefix=old_prefix,
            new_prefix=new_prefix,
            task_id=task_id
        )
        return schemas.Response(
            success=success,
            message=message,
            data={
                "updated_records": updated_records,
                "updated_extrainfo": updated_extrainfo
            }
        )

    def sync_watch_history(self, direction: str = "from_server", force: bool = False) -> schemas.TaskStatus:
        """将观看历史同步丢给 Celery，立即返回任务状态。"""
        logger.info(f"Enqueue watch history sync, direction={direction}, force={force}")
        return CeleryTaskService(self.session).enqueue_unique(
            celery_sync_watch_history,
            TASK_WATCH_HISTORY_SYNC,
            detail=f"{direction}|{int(bool(force))}",
            name="同步观看历史",
            direction=direction,
            force=force,
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

    def get_scrapinglib_version(self) -> schemas.ScrapinglibVersion:
        """检测 scrapinglib 当前版本与 PyPI 最新版本"""
        current = get_installed_version()
        try:
            latest = fetch_latest_version(get_active_proxy(self.session))
            update_available = is_newer(latest, current)
            message = "有新版本可更新" if update_available else "已是最新版本"
            return schemas.ScrapinglibVersion(
                current=current,
                latest=latest,
                update_available=update_available,
                message=message,
            )
        except Exception as e:
            logger.warning("Failed to fetch scrapinglib latest version: %s", e)
            return schemas.ScrapinglibVersion(
                current=current,
                latest=None,
                update_available=False,
                message=f"无法获取最新版本: {e}",
                success=False,
            )

    def update_scrapinglib(self) -> schemas.ScrapinglibVersion:
        """升级 scrapinglib 并在当前进程及 Celery worker 中重新加载"""
        info = self.get_scrapinglib_version()
        if not info.update_available:
            if not info.latest:
                return info
            info.message = "已是最新版本，无需更新"
            return info

        ok, output = pip_install_upgrade()
        if not ok:
            info.message = f"更新失败: {output[-500:] if output else 'pip install 失败'}"
            info.success = False
            return info

        try:
            from bonita.utils.scrapinglib_pkg import ensure_extra_site_packages
            ensure_extra_site_packages()
            reload_modules()
        except Exception as e:
            logger.warning("Reload scrapinglib in API process failed: %s", e)

        try:
            celery_reload_scrapinglib.delay()
        except Exception as e:
            logger.warning("Failed to notify celery to reload scrapinglib: %s", e)

        current = get_installed_version()
        latest = info.latest
        update_available = is_newer(latest, current) if latest else False
        return schemas.ScrapinglibVersion(
            current=current,
            latest=latest,
            update_available=update_available,
            message=f"已更新到 {current}" if not update_available else f"已安装，当前版本 {current}",
        )
