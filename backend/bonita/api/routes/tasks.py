import json
import logging
from typing import Any
from fastapi import APIRouter

from bonita import schemas, main
from bonita.api.deps import SessionDep
from bonita.db import SessionFactory
from bonita.db.models.task import TransferConfig
from bonita.celery_tasks.tasks import celery_transfer_entry

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run/{id}", response_model=schemas.TaskStatus)
async def run_transfer_task(
        session: SessionDep,
        id: int) -> Any:
    """
    立即执行任务
    """
    logger.info(f"run transfer task: {id}")
    task_conf = session.get(TransferConfig, id)
    task_dict = task_conf.to_dict()
    task = celery_transfer_entry.delay(task_dict)
    return schemas.TaskStatus(id=task.id, name=task_conf.name, transfer_config=task_conf.id)


@router.get("/status/{task_id}", response_model=schemas.TaskStatus)
def get_task_status(task_id: str) -> Any:
    """
    查看单个任务状态
    """
    task_result = main.celery.AsyncResult(task_id)
    try:
        detail = json.dumps(task_result.result)
    except:
        detail = ""
    return schemas.TaskStatus(id=task_id, status=task_result.state, detail=detail)


@router.get("/status", response_model=list[schemas.TaskStatus])
def get_all_tasks_status() -> Any:
    """ 获取所有任务状态
    """
    inspector = main.celery.control.inspect()
    active_tasks = inspector.active() or {}

    all_tasks = []

    # 处理活跃任务
    for worker, tasks in active_tasks.items():
        for task in tasks:
            all_tasks.append(schemas.TaskStatus(
                id=task['id'],
                status='ACTIVE',
                detail=json.dumps(task.get('kwargs', {}))
            ))

    return all_tasks
