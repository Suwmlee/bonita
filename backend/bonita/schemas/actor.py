from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ActorAliasPublic(BaseModel):
    id: int
    name: str
    createtime: datetime

    class Config:
        from_attributes = True


class ActorBase(BaseModel):
    name: str
    photo: Optional[str] = ""
    birth_date: Optional[date] = None
    outline: Optional[str] = ""


class ActorCreate(ActorBase):
    aliases: List[str] = Field(default_factory=list, description="别名列表；主名会自动加入")


class ActorUpdate(BaseModel):
    name: Optional[str] = None
    photo: Optional[str] = None
    birth_date: Optional[date] = None
    outline: Optional[str] = None
    aliases: Optional[List[str]] = None


class ActorPublic(ActorBase):
    id: int
    aliases: List[ActorAliasPublic] = Field(default_factory=list)
    createtime: datetime
    updatetime: datetime

    class Config:
        from_attributes = True


class ActorEntityCollection(BaseModel):
    """演员实体列表（区别于 metadata 页 ActorSummary 墙）"""
    data: List[ActorPublic]
    count: int


class ActorResolveResult(BaseModel):
    """别名解析结果：命中则给出主名，未命中保留原文"""

    input: str
    resolved: str
    actor_id: Optional[int] = None
    matched: bool = False
