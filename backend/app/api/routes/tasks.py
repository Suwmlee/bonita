
from typing import Any
from fastapi import APIRouter

from app import schemas
from app.api.deps import CurrentUser, SessionDep
from app.db.models.task import TransferTask


router = APIRouter()


@router.get("/all", response_model=schemas.TasksPublic)
def get_all_tasks(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有任务.
    """
    tasks = session.query(TransferTask).offset(skip).limit(limit).all()
    count = session.query(TransferTask).count()

    task_list = [schemas.TaskPublic.model_validate(task) for task in tasks]
    return schemas.TasksPublic(data=task_list, count=count)


@router.post("/", response_model=schemas.TaskPublic)
def create_task(
    *, session: SessionDep, current_user: CurrentUser, task_in: schemas.TaskCreate
) -> Any:
    """
    创建新任务
    """
    task = TransferTask(task_in)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
