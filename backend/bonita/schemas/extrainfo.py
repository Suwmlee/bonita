from typing import Optional
from pydantic import BaseModel


class ExtraInfoBase(BaseModel):
    filepath: str
    number: str
    tag: Optional[str] = None
    partNumber: int
    specifiedsource: Optional[str] = None
    specifiedurl: Optional[str] = None


class ExtraInfoPublic(ExtraInfoBase):
    id: int

    class Config:
        from_attributes = True
