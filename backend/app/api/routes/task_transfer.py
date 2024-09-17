
from typing import Any
from fastapi import APIRouter, HTTPException

from app import schemas
from app.api.deps import CurrentUser, SessionDep
from app.db.models.task import TransferTask
from app.tasks.tasks import test_app_task

router = APIRouter()


@router.get("/all", response_model=schemas.TransferTasksPublic)
def get_all_tasks(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有任务.
    """
    tasks = session.query(TransferTask).offset(skip).limit(limit).all()
    count = session.query(TransferTask).count()

    task_list = [schemas.TransferTaskPublic.model_validate(task) for task in tasks]
    return schemas.TransferTasksPublic(data=task_list, count=count)


@router.post("/", response_model=schemas.TransferTaskPublic)
def create_task(
    *, session: SessionDep, current_user: CurrentUser, task_in: schemas.TransferTaskCreate
) -> Any:
    """
    创建新任务
    """
    task_info = task_in.__dict__
    task = TransferTask(**task_info)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.put("/{id}", response_model=schemas.TransferTaskPublic)
def update_task(
    session: SessionDep,
    id: int,
    task_in: schemas.TransferTaskPublic,
) -> Any:
    """
    更新任务
    """
    task = session.get(TransferTask, id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    update_dict = task_in.model_dump(exclude_unset=True)
    task.update(session, update_dict)
    session.commit()
    session.refresh(task)
    return task


@router.post("/run/{id}")
def run_transfer_task(id: int) -> Any:
    """
    立即执行任务
    """
    print(f"post task {id}")
    task = test_app_task.delay(5)
    return task.id
