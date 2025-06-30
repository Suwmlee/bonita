import json
import logging
from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas, main
from bonita.api.deps import SessionDep
from bonita.db.models.task import TransferConfig, CeleryTask
from bonita.celery_tasks.tasks import celery_transfer_entry, celery_transfer_group
from bonita.services.celery_service import CeleryTaskService
from bonita.core.enums import TaskStatusEnum

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
    task_conf = session.get(TransferConfig, id)
    if not task_conf:
        raise HTTPException(status_code=404, detail="Task not found")
    task_dict = task_conf.to_dict()

    task_type = 'TransferAll'
    detail = id
    if path_param.path:
        # 如果提供了path参数，针对指定路径运行任务
        task_type = 'TransferGroup'
        detail = path_param.path.strip()
        task = celery_transfer_group.delay(task_dict, path_param.path.strip(), True)
    else:
        task = celery_transfer_entry.delay(task_dict)
    return schemas.TaskStatus(id=task.id,
                              name=task_conf.name,
                              status=TaskStatusEnum.PENDING,
                              task_type=task_type,
                              detail=str(detail),
                              progress=0.0,
                              step='任务已启动')


@router.get("/status", response_model=list[schemas.TaskStatus])
def get_all_tasks_status(session: SessionDep) -> Any:
    """ 获取所有任务状态
    """
    celery_service = CeleryTaskService(session)
    # 获取所有活跃任务（进行中和等待中的任务）
    active_tasks = celery_service.get_active_tasks()

    all_tasks = []
    for task in active_tasks:
        all_tasks.append(schemas.TaskStatus(
            id=task.task_id,
            name=task.task_type or "unknown",
            status=task.status,  # 直接传入枚举对象
            detail=task.detail,  # 保持原有的detail内容
            task_type=task.task_type,
            progress=task.progress,
            step=task.step,
            result=task.result,
            error_message=task.error_message,
            created_at=task.created_at,
            updatetime=task.updatetime
        ))

    return all_tasks
