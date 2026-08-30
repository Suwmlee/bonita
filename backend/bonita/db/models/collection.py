from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from bonita.db import Base


class Collection(Base):
    """要从媒体服务器同步的合集白名单"""
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_collection_source_external_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, default="emby", index=True, comment="媒体源 emby/jellyfin")
    external_id = Column(String, nullable=False, index=True, comment="远端合集 Id")
    name = Column(String, nullable=False, comment="合集名称")
    image_tag = Column(String, comment="远端海报 ImageTag")
    item_count = Column(Integer, default=0, comment="远端合集当前成员数")
    matched_count = Column(Integer, default=0, comment="Bonita 合集成员数")
    last_sync_at = Column(DateTime, comment="上次同步成员时间")
    createtime = Column(DateTime, default=datetime.now, comment="创建时间")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    members = relationship(
        "CollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan",
    )


class CollectionItem(Base):
    """合集与本地媒体项的成员关系"""
    __table_args__ = (
        UniqueConstraint("collection_id", "media_item_id", name="uq_collection_media_item"),
    )

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(
        Integer,
        ForeignKey("collection.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_item_id = Column(
        Integer,
        ForeignKey("mediaitem.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_item_id = Column(String, index=True, comment="远端条目 Id，回写时用")
    createtime = Column(DateTime, default=datetime.now, comment="创建时间")

    collection = relationship("Collection", back_populates="members")
    media_item = relationship("MediaItem")
