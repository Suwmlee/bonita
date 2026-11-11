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


class ActorHomonymPublic(BaseModel):
    """同名候选演员"""

    id: int
    name: str
    photo: Optional[str] = None
    count: int = 0


class MetadataCreditPublic(BaseModel):
    """某片的一行出演"""

    actor_id: int
    actor_name: str
    credit_name: str
    sort: int = 0
    photo: Optional[str] = None
    homonym_count: int = 1


class CreditRematchRequest(BaseModel):
    to_actor_id: int


class CreditSplitRequest(BaseModel):
    name: Optional[str] = None


class CreditSplitResult(BaseModel):
    actor: ActorPublic
    credits: List[MetadataCreditPublic]
