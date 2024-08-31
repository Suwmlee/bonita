
from typing import Any
from fastapi import APIRouter

from app import schemas
from app.api.deps import SessionDep
from app.db.models.task import TransferTask


router = APIRouter()


@router.get("/all", response_model=schemas.TasksPublic)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """
    tasks = session.query(TransferTask).offset(skip).limit(limit).all()
    count = session.query(TransferTask).count()

    task_list = [schemas.TaskPublic.model_validate(task) for task in tasks]
    return schemas.TasksPublic(data=task_list, count=count)
