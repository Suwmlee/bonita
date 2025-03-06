import logging
from fastapi import APIRouter

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.celery_tasks.tasks import celery_import_nfo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/importnfo")
async def run_import_nfo(
        session: SessionDep,
        folder_path: str):
    """ 导入NFO信息
    """
    logger.info(f"run import nfo: {folder_path}")
    task = celery_import_nfo.delay(folder_path)
    return schemas.TaskStatus(id=task.id,
                              name="import nfo",
                              status='ACTIVE')


@router.get("/embyscan")
async def get_emby_scan(session: SessionDep):
    """ 扫描emby
    """
    logger.info("run emby scan")
