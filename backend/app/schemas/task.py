from typing import List, Optional
from pydantic import BaseModel


class TransferTaskBase(BaseModel):
    """
    Shared properties
    """
    name: str
    description: str
    task_type: int = 1
    enabled: bool = True
    auto_watch: bool = False
    transfer_type: int = 1
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
    transfer_type: int
    source_folder: str
