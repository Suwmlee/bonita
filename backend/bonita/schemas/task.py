from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from bonita.utils.filehelper import OperationMethod
from bonita.core.enums import TaskStatusEnum


class TaskBase(BaseModel):
    id: str
    name: Optional[str] = None


class TaskStatus(TaskBase):
    status: Optional[TaskStatusEnum] = None
    detail: Optional[str] = None
    task_type: Optional[str] = None
    progress: Optional[float] = None
    step: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updatetime: Optional[datetime] = None


class TransferConfigBase(BaseModel):
    """
    Shared properties
    """
    name: str
    description: str
    enabled: bool = True
    content_type: int = 1
    operation: OperationMethod = OperationMethod.HARD_LINK
    auto_watch: bool = False
    clean_others: bool = False
    optimize_name: bool = False
    source_folder: str
    output_folder: str
    failed_folder: Optional[str] = None
    escape_folder: Optional[str] = None
    escape_literals: Optional[str] = None
    escape_size: Optional[int] = 1
    threads_num: Optional[int] = 1
    sc_enabled: bool = False
    sc_id: Optional[int] = None


class TransferConfigPublic(TransferConfigBase):
    """
    Properties to return via API, id is always required
    """
    id: int

    class Config:
        from_attributes = True


class TransferConfigsPublic(BaseModel):
    data: List[TransferConfigPublic]
    count: int


class TransferConfigCreate(TransferConfigBase):
    operation: OperationMethod
    source_folder: str


class TaskPathParam(BaseModel):
    path: Optional[str] = None


class ToolArgsParam(BaseModel):
    """
    工具参数请求
    """
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    arg3: Optional[str] = None
