import logging
from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.celery_service import CeleryTaskService
from bonita.services.transfer_config_service import TransferConfigService
from bonita.schemas.response import Response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run/{id}", response_model=schemas.TaskStatus)
async def run_transfer_task(
        session: SessionDep,
        id: int,
        path_param: schemas.TaskPathParam) -> Any:
    """ 立即执行任务
    """
    logger.info(f"run transfer task: {id}")
    status = TransferConfigService(session).run_transfer(id, path_param.path)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.get("/status", response_model=list[schemas.TaskStatus])
def get_all_tasks_status(
    session: SessionDep,
    limit: int = 100
) -> Any:
    """ 获取所有任务状态
    """
    celery_service = CeleryTaskService(session)
    active_tasks = celery_service.get_all_tasks(limit=limit)

    all_tasks = []
    for task in active_tasks:
        all_tasks.append(schemas.TaskStatus(
            task_id=task.task_id,
            name=task.task_type or "unknown",
            status=task.status,
            detail=task.detail,
            task_type=task.task_type,
            progress=task.progress,
            step=task.step,
            result=task.result,
            error_message=task.error_message,
            created_at=task.created_at,
            updatetime=task.updatetime
        ))

    return all_tasks


@router.post("/cleanup/running", response_model=Response)
def cleanup_running_tasks(session: SessionDep) -> Any:
    """ 清理当前进行中的任务，批量标记为取消
    """
    celery_service = CeleryTaskService(session)
    updated = celery_service.revoke_active_tasks("被清理为取消")
    return Response(success=True, message="已标记取消", data={"updated": updated})
