from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from bonita.utils.filehelper import OperationMethod
from bonita.core.enums import TaskStatusEnum


class TaskStatus(BaseModel):
    task_id: str
    name: Optional[str] = None
    status: TaskStatusEnum
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


class SyncDirection(str, Enum):
    """媒体服务器同步方向。from_emby / to_emby 为兼容别名。"""
    FROM_SERVER = "from_server"
    TO_SERVER = "to_server"
    FROM_EMBY = "from_emby"
    TO_EMBY = "to_emby"


class EmbySyncParam(BaseModel):
    """
    媒体服务器观看同步参数。路径仍为 /tools/sync/emby。
    """
    direction: SyncDirection = Field(
        default=SyncDirection.FROM_SERVER,
        description="from_server: 远端 → Bonita；to_server: Bonita → 远端",
    )
    force: bool = Field(
        default=False,
        description="强制覆盖对端已有的已看/收藏状态",
    )
