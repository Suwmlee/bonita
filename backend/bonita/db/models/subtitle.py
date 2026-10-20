from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from bonita.db import Base


class Subtitle(Base):
    """字幕库

    第一期按番号归档。identity_type / identity_key 预留给以后的 IMDB 等标识。
    """

    id = Column(Integer, primary_key=True, index=True)
    identity_type = Column(String, default="number", index=True, comment="标识类型")
    identity_key = Column(String, default="", index=True, comment="标识值，番号大写")
    language = Column(String, default="zh-Hans", comment="语言")
    part_number = Column(Integer, default=0, server_default="0", comment="部次，0 表示无分集")
    original_name = Column(String, default="", comment="上传时的文件名")
    stored_path = Column(String, default="", comment="相对字幕目录的存储路径")
    file_extension = Column(String, default="", comment="扩展名，含点")

    createtime = Column(DateTime, default=datetime.now, comment="创建时间")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
