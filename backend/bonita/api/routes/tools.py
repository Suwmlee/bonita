import logging
from fastapi import APIRouter

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.tool_service import ToolService

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
        return schemas.TaskStatus(id=None,
                                  name="import nfo",
                                  status='FAILED')


@router.get("/embyscan", response_model=schemas.TaskStatus)
async def run_emby_scan(
        session: SessionDep,
        folder_args: schemas.ToolArgsParam):
    """ 扫描emby
    """
    tool_service = ToolService(session)
    return tool_service.emby_scan(folder_args)


@router.post("/sync/emby", response_model=schemas.Response)
async def sync_emby_watch_history(
        session: SessionDep):
    """ 同步emby watch history
    """
    tool_service = ToolService(session)
    return tool_service.sync_emby_watch_history()


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
