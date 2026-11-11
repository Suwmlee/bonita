from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
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
    credits = relationship(
        "MetadataActor",
        back_populates="actor",
    )


class ActorAlias(Base):
    """演员别名索引：刮削名匹配到 Actor；同名可对应多人（取作品数最多，人工再改挂）"""

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


class MetadataActor(Base):
    """元数据出演：用 actor_id 关联；credit_name 保留刮削原文"""

    __tablename__ = "metadata_actor"
    __table_args__ = (
        UniqueConstraint("metadata_id", "actor_id", name="uq_metadata_actor"),
    )

    id = Column(Integer, primary_key=True, index=True)
    metadata_id = Column(
        Integer,
        ForeignKey("metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = Column(
        Integer,
        ForeignKey("actor.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    credit_name = Column(String, nullable=False, default="", comment="这部片子的刮削出演名")
    sort = Column(Integer, nullable=False, default=0, comment="写出顺序")
    createtime = Column(DateTime, default=datetime.now, comment="创建时间")

    actor = relationship("Actor", back_populates="credits")
    metadata_row = relationship("Metadata", foreign_keys=[metadata_id])
