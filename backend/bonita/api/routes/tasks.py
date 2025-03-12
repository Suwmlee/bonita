import json
import logging
from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas, main
from bonita.api.deps import SessionDep
from bonita.db.models.task import TransferConfig
from bonita.celery_tasks.tasks import celery_transfer_entry, celery_transfer_group

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

    if path_param.path:
        # 如果提供了path参数，针对指定路径运行任务
        task = celery_transfer_group.delay(task_dict, path_param.path.strip(), True)
    else:
        task = celery_transfer_entry.delay(task_dict)
    return schemas.TaskStatus(id=task.id,
                              name=task_conf.name,
                              transfer_config=task_conf.id,
                              scraping_config=task_conf.sc_id if task_conf.sc_enabled else 0,
                              status='ACTIVE')


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
            args = task.get('args', [])
            task_id = 0
            task_scid = 0
            try:
                if isinstance(args, list) and len(args) > 0:
                    # transferConfig是第一个参数
                    first_arg = args[0]
                    if isinstance(first_arg, dict):
                        if 'id' in first_arg and 'sc_id' in first_arg:
                            task_id = first_arg['id']
                            if first_arg['sc_enabled']:
                                task_scid = first_arg['sc_id']
            except Exception as e:
                print(f"Error extracting task info: {str(e)}")

            all_tasks.append(schemas.TaskStatus(
                id=task['id'],
                name=task['name'],
                transfer_config=task_id,
                scraping_config=task_scid,
                status='ACTIVE',
                detail=json.dumps(args)
            ))

    return all_tasks
