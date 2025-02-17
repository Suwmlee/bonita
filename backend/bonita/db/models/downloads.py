
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from bonita.db import Base


class Downloads(Base):
    """ 下载的文件
    """
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False, comment="下载链接")
    filepath = Column(String, nullable=False, comment="文件路径")
    updatetime = Column(DateTime, default=datetime.now, comment="更新时间")
