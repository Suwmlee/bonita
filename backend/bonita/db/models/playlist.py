from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from bonita.db import Base


class Playlist(Base):
    """要从媒体服务器同步的播放列表白名单（音乐；smart 可拉，回写走「· 同步」普通列表）。"""

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_playlist_source_external_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, default="plex", index=True, comment="媒体源 plex")
    external_id = Column(
        String,
        nullable=False,
        index=True,
        comment="稳定远端 Id，优先 playlist guid",
    )
    rating_key = Column(String, index=True, comment="当前 Plex ratingKey 缓存（拉取源）")
    write_rating_key = Column(
        String,
        index=True,
        comment="回写目标 ratingKey；smart 时为「原名 · 同步」普通列表",
    )
    name = Column(String, nullable=False, comment="播放列表名称")
    is_smart = Column(Boolean, default=False, server_default="0", comment="是否 Plex smart 列表")
    item_count = Column(Integer, default=0, comment="远端成员数")
    matched_count = Column(Integer, default=0, comment="本地成员快照数")
    last_sync_at = Column(DateTime, comment="上次同步成员时间")
    createtime = Column(DateTime, default=datetime.now, comment="创建时间")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    members = relationship(
        "PlaylistItem",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistItem.sort_index",
    )


class PlaylistItem(Base):
    """播放列表成员快照；允许尚未对上本地媒体项。"""

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(
        Integer,
        ForeignKey("playlist.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_item_id = Column(
        Integer,
        ForeignKey("mediaitem.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="可选，对上本地媒体项时填写",
    )
    external_item_id = Column(String, index=True, comment="远端 track ratingKey")
    external_guid = Column(String, index=True, comment="远端 track guid")
    playlist_item_id = Column(String, index=True, comment="Plex playlistItemID，删成员用")
    path = Column(String, comment="音轨文件路径")
    title = Column(String, comment="曲名")
    artist = Column(String, comment="艺人")
    album = Column(String, comment="专辑")
    sort_index = Column(Integer, default=0, comment="列表内顺序")
    createtime = Column(DateTime, default=datetime.now, comment="创建时间")

    playlist = relationship("Playlist", back_populates="members")
    media_item = relationship("MediaItem")
