from typing import Optional
from pydantic import BaseModel


class ExtraInfoBase(BaseModel):
    filepath: str
    number: str
    tag: Optional[str] = None
    partNumber: int = 0
    crop: Optional[bool] = True
    specifiedsource: Optional[str] = None
    specifiedurl: Optional[str] = None


class ExtraInfoPublic(ExtraInfoBase):
    id: Optional[int] = None
    filepath: Optional[str] = None
    number: Optional[str] = None
    partNumber: Optional[int] = None

    class Config:
        from_attributes = True
