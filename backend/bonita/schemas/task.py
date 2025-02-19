from typing import List, Optional
from pydantic import BaseModel

from bonita.utils.filehelper import OperationMethod


class TaskBase(BaseModel):
    id: str


class TaskStatus(TaskBase):
    status: Optional[str] = None
    detail: Optional[str] = None


class TransferTaskBase(BaseModel):
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
    output_folder: Optional[str] = None
    failed_folder: Optional[str] = None
    escape_folder: Optional[str] = None
    escape_literals: Optional[str] = None
    escape_size: Optional[int] = 1
    threads_num: Optional[int] = 1
    sc_enabled: bool = False
    sc_id: Optional[int] = None


class TransferTaskPublic(TransferTaskBase):
    """
    Properties to return via API, id is always required
    """
    id: int

    class Config:
        from_attributes = True


class TransferTasksPublic(BaseModel):
    data: List[TransferTaskPublic]
    count: int


class TransferTaskCreate(TransferTaskBase):
    operation: OperationMethod
    source_folder: str
