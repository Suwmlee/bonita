from typing import List
from pydantic import BaseModel


# Shared properties
class TaskBase(BaseModel):
    name: str


# Properties to return via API, id is always required
class TaskPublic(TaskBase):
    id: int

    class Config:
        from_attributes = True


class TasksPublic(BaseModel):
    data: List[TaskPublic]
    count: int


class TaskCreate(TaskBase):
    description: str
    task_type: int

    sc_enabled: bool | None
    sc_id: int | None
