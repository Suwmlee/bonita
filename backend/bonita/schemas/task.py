from typing import List, Optional
from pydantic import BaseModel

from bonita.utils.filehelper import OperationMethod


class TaskBase(BaseModel):
    id: str
    name: Optional[str] = None
    transfer_config: Optional[int] = None
    scraping_config: Optional[int] = None


class TaskStatus(TaskBase):
    status: Optional[str] = None
    detail: Optional[str] = None


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
