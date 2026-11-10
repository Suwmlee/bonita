from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from bonita.db import Base


class Actor(Base):
    """演员词典：主名 + 头像；别名走 ActorAlias，供刮削统一替换"""

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True, comment="主名（写出用）")
    photo = Column(String, default="", comment="头像 URL，展示时按需缓存")
    birth_date = Column(Date, comment="出生日期")
    outline = Column(String, default="", comment="概要")

    createtime = Column(DateTime, default=datetime.now, comment="创建时间")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    aliases = relationship(
        "ActorAlias",
        back_populates="actor",
        cascade="all, delete-orphan",
    )


class ActorAlias(Base):
    """演员别名索引：刮削名精确匹配后落到 Actor.name"""

    __table_args__ = (
        UniqueConstraint("name", name="uq_actoralias_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(
        Integer,
        ForeignKey("actor.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False, index=True, comment="别名或主名")
    createtime = Column(DateTime, default=datetime.now, comment="创建时间")

    actor = relationship("Actor", back_populates="aliases")
