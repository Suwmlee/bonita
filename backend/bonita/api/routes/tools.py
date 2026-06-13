import logging
import uuid
from fastapi import APIRouter

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.tool_service import ToolService
from bonita.core.enums import TaskStatusEnum

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/importnfo", response_model=schemas.TaskStatus)
async def run_import_nfo(
        session: SessionDep,
        folder_args: schemas.ToolArgsParam):
    """ 导入NFO信息
    """
    tool_service = ToolService(session)
    if folder_args.arg1 and folder_args.arg2:
        return tool_service.import_nfo(folder_args.arg1, folder_args.arg2)
    else:
        return schemas.TaskStatus(task_id=str(uuid.uuid4()),
                                  name="import nfo",
                                  status=TaskStatusEnum.FAILURE,
                                  task_type='ImportNFO',
                                  progress=0.0,
                                  step='参数错误',
                                  error_message='缺少必要参数')


@router.get("/embyscan", response_model=schemas.TaskStatus)
async def run_emby_scan(
        session: SessionDep,
        folder_args: schemas.ToolArgsParam):
    """ 扫描emby
    """
    tool_service = ToolService(session)
    return tool_service.emby_scan(folder_args)


@router.post("/records/path", response_model=schemas.Response)
async def sync_record_path(
        session: SessionDep,
        params: schemas.TransRecordsPathSyncParam):
    """批量替换转移记录源路径前缀

    当任务更改了源文件路径后，可通过此接口将历史转移记录的路径前缀批量替换为新路径，
    同时同步更新关联的 ExtraInfo，避免自定义内容失效。

    Args:
        params: 路径替换参数
            - old_prefix: 旧路径前缀
            - new_prefix: 新路径前缀
            - task_id: 可选，仅更新指定任务的记录
    """
    tool_service = ToolService(session)
    return tool_service.sync_record_path(
        old_prefix=params.old_prefix,
        new_prefix=params.new_prefix,
        task_id=params.task_id
    )


@router.post("/sync/emby", response_model=schemas.Response)
async def sync_emby_watch_history(
        session: SessionDep,
        params: schemas.EmbySyncParam):
    """ 同步 Emby 和 Bonita 之间的观看记录
    
    Args:
        params: Emby 同步参数
            - direction: 同步方向 ("from_emby" 或 "to_emby")，默认为 "from_emby"
                * "from_emby": 从 Emby 同步到 Bonita（默认）
                * "to_emby": 从 Bonita 回写到 Emby（仅处理有 number 的项目）
            - force: 是否强制覆盖数据，默认为 false
                * direction="from_emby" 时：是否强制覆盖本地数据（包括喜爱标记）
    """
    tool_service = ToolService(session)
    return tool_service.sync_emby_watch_history(direction=params.direction.value, force=params.force)


@router.post("/cleanup", response_model=schemas.Response)
async def cleanup_data(
        session: SessionDep,
        params: schemas.ToolArgsParam):
    """ 清理下载器、转移记录和实际文件

    Args:
        arg1: 强制删除 ("true"/"false") 
    """
    # 获取是否删除文件的参数，默认为false
    delete_files = params.arg1.lower() == "true" if params.arg1 else False

    # 使用ToolService处理逻辑
    tool_service = ToolService(session)
    return tool_service.cleanup_data(delete_files)
