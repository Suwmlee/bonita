
from typing import Any
from fastapi import APIRouter

from app import schemas, main
from app.api.deps import SessionDep
from app.db.models.task import TransferTask
from app.celery_tasks.tasks import celery_run_task


router = APIRouter()


@router.post("/run/{id}", response_model=schemas.TaskBase)
async def run_transfer_task(
        session: SessionDep,
        id: int) -> Any:
    """
    立即执行任务
    """
    task_conf = session.get(TransferTask, id)
    # task = celery_run_task.apply_async(args=6)
    task = celery_run_task.delay(5)
    return schemas.TaskBase(id=task.id)


@router.get("/{task_id}", response_model=schemas.TaskStatus)
def get_task_status(task_id: str) -> Any:
    """
    查看任务状态
    """
    task_result = main.celery.AsyncResult(task_id)
    detail = task_result.result if task_result.result else ""
    return schemas.TaskStatus(id=task_id, status=task_result.state, detail=detail)
