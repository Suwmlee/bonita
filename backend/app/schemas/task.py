from typing import List, Optional
from pydantic import BaseModel


# Shared properties
class TaskBase(BaseModel):
    name: str
    description: str
    task_type: int = 1
    enabled: bool = True
    auto_watch: bool = False
    transfer_type: int = 1
    source_folder: Optional[str] = None
    output_folder: Optional[str] = None
    failed_folder: Optional[str] = None
    escape_folder: Optional[str] = None
    escape_literals: Optional[str] = None
    escape_size: Optional[int] = 1
    threads_num: Optional[int] = 1
    sc_enabled: bool = False
    sc_id: Optional[int] = None

# Properties to return via API, id is always required


class TaskPublic(TaskBase):
    id: int

    class Config:
        from_attributes = True


class TasksPublic(BaseModel):
    data: List[TaskPublic]
    count: int


class TaskCreate(TaskBase):
    scraping_sites: Optional[str] = None
    location_rule: Optional[str] = None
    naming_rule: Optional[str] = None
    max_title_len: Optional[str] = None
