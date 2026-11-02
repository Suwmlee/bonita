from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from bonita.schemas.extrainfo import ExtraInfoPublic


class TransferRecordBase(BaseModel):
    """
    Shared properties
    """
    srcname: str
    srcpath: str
    srcfolder: str
    task_id: int

    success: Optional[bool] = False
    ignored: bool = False
    locked: bool = False
    deleted: bool = False
    srcdeleted: bool = False

    forced_name: Optional[str] = None
    top_folder: Optional[str] = None
    second_folder: Optional[str] = None
    isepisode: Optional[bool] = False
    season: Optional[int] = -1
    episode: Optional[int] = -1
    part_number: Optional[int] = 0
    linkpath: Optional[str] = None
    destpath: Optional[str] = None
    output_folder: Optional[str] = ""

    updatetime: Optional[datetime] = None
    deadtime: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransferRecordPublic(TransferRecordBase):
    """
    Properties to return via API, id is always required
    """
    id: int

    class Config:
        from_attributes = True


class TransferRecordsPublic(BaseModel):
    data: List[TransferRecordPublic]
    count: int


class RecordPublic(BaseModel):
    transfer_record: TransferRecordPublic
    extra_info: Optional[ExtraInfoPublic] = None
    subtitle_count: int = 0

    class Config:
        from_attributes = True

class RecordsPublic(BaseModel):
    data: List[RecordPublic]
    count: int


class RecordGroupPublic(BaseModel):
    """同一番号、且能对上 metadata 的转移记录。"""
    key: str
    number: str
    title: str = ""
    cover: str = ""
    crop: bool = True
    record_count: int
    latest_updatetime: Optional[datetime] = None
    records: List[RecordPublic]

    class Config:
        from_attributes = True


class RecordGroupsPublic(BaseModel):
    data: List[RecordGroupPublic]
    count: int


class TransRecordsPathSyncParam(BaseModel):
    """转移记录路径批量替换参数"""
    old_prefix: str = Field(..., description="旧路径前缀")
    new_prefix: str = Field(..., description="新路径前缀")
    task_id: Optional[int] = Field(default=None, description="可选，仅更新指定任务的记录")
