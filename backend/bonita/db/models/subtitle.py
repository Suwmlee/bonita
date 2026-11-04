from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from bonita.db import Base


class Subtitle(Base):
    """字幕库。挂在媒体项上，番号和 IMDb 由媒体项区分。"""

    id = Column(Integer, primary_key=True, index=True)
    media_item_id = Column(
        Integer,
        ForeignKey("mediaitem.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        comment="关联的媒体项",
    )
    language = Column(String, default="zh-Hans", comment="语言")
    part_number = Column(Integer, default=0, server_default="0", comment="部次，0 表示无分集")
    original_name = Column(String, default="", comment="上传时的文件名")
    stored_path = Column(String, default="", comment="相对字幕目录的存储路径")
    file_extension = Column(String, default="", comment="扩展名，含点")
    preferred = Column(Boolean, default=False, server_default="0", comment="当前投递这一份")
    delivered_paths = Column(Text, default="", comment="上次写到影片旁边的路径，JSON 数组")

    createtime = Column(DateTime, default=datetime.now, comment="创建时间")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
