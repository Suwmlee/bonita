
from sqlalchemy import Column, Index, Integer, String, Boolean, func

from bonita.db import Base


class ExtraInfo(Base):
    """ 自定义额外信息
    """
    id = Column(Integer, primary_key=True, index=True)
    filepath = Column(String, default="", nullable=False, index=True, comment="文件路径")
    number = Column(String, default="", nullable=False, comment="编号")
    tag = Column(String, default="", comment="标签（用于分类）")
    crop = Column(Boolean, default=True, comment="是否裁切poster")
    specifiedsource = Column(String, default="", comment="指定来源")
    specifiedurl = Column(String, default="", comment="指定链接")

    __table_args__ = (
        Index("ix_extrainfo_number_key", func.upper(func.trim(number))),
    )
