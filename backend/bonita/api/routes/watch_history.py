
import logging
from fastapi import APIRouter

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.modules.media_service.sync import sync_emby_history

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sync/emby", response_model=schemas.Response)
async def sync_emby_watch_history(
        session: SessionDep):
    """ 同步emby watch history
    """
    logger.info("sync emby watch history")
    sync_emby_history(session)

    return schemas.Response(success=True,
                            message="sync emby watch history success")
