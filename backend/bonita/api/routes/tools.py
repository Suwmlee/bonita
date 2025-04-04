import logging
import os
import datetime
from fastapi import APIRouter

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.celery_tasks.tasks import celery_import_nfo
from bonita.modules.media_service.sync import sync_emby_history

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/importnfo", response_model=schemas.TaskStatus)
async def run_import_nfo(
        session: SessionDep,
        folder_args: schemas.ToolArgsParam):
    """ 导入NFO信息
    """
    if folder_args.arg1 and folder_args.arg2:
        folder_path = folder_args.arg1
        option = folder_args.arg2
        logger.info(f"run import nfo: {folder_path}")
        task = celery_import_nfo.delay(folder_path, option)
        return schemas.TaskStatus(id=task.id,
                                  name="import nfo",
                                  status='ACTIVE')
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
    logger.info("run emby scan")
    return schemas.TaskStatus(id=None,
                              name="emby scan",
                              status='FAILED')


@router.post("/sync/emby", response_model=schemas.Response)
async def sync_emby_watch_history(
        session: SessionDep):
    """ 同步emby watch history
    """
    logger.info("sync emby watch history")
    sync_emby_history(session)

    return schemas.Response(success=True,
                            message="sync emby watch history success")
