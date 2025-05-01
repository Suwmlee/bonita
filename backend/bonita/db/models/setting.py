from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from bonita.db import Base


class SystemSetting(Base):
    """ 系统设置
    """
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=True, default="")
    description = Column(String, default="")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
