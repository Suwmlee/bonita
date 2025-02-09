
import json
from typing import Any
from fastapi import APIRouter

from bonita import schemas, main
from bonita.api.deps import SessionDep
from bonita.db.models.task import TransferTask
from bonita.celery_tasks.tasks import celery_transfer_entry

router = APIRouter()


@router.post("/run/{id}", response_model=schemas.TaskBase)
async def run_transfer_task(
        session: SessionDep,
        id: int) -> Any:
    """
    立即执行任务
    """
    task_conf = session.get(TransferTask, id)
    task_dict = task_conf.to_dict()
    task = celery_transfer_entry.delay(task_dict)
    return schemas.TaskBase(id=task.id)


@router.get("/{task_id}", response_model=schemas.TaskStatus)
def get_task_status(task_id: str) -> Any:
    """
    查看任务状态
    """
    task_result = main.celery.AsyncResult(task_id)
    try:
        # detail = task_result.traceback if task_result.failed() else task_result.result
        detail = json.dumps(task_result.result)
    except:
        detail = ""
    return schemas.TaskStatus(id=task_id, status=task_result.state, detail=detail)
