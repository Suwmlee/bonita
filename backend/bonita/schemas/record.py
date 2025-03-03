from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from bonita.schemas.extrainfo import ExtraInfoPublic


class TransferRecordBase(BaseModel):
    """
    Shared properties
    """
    srcname: str
    srcpath: str
    srcfolder: Optional[str] = None

    ignored: bool = False
    locked: bool = False
    deleted: bool = False

    forced_name: Optional[str] = None
    top_folder: Optional[str] = None
    second_folder: Optional[str] = None
    isepisode: Optional[bool] = False
    season: Optional[int] = -1
    episode: Optional[int] = -1
    linkpath: Optional[str] = None
    destpath: Optional[str] = None

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

    class Config:
        from_attributes = True

class RecordsPublic(BaseModel):
    data: List[RecordPublic]
    count: int
