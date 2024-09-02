from typing import List, Optional
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

    sc_enabled: bool
    sc_id: Optional[int] = None
