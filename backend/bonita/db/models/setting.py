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

    @classmethod
    def get_setting(cls, session, key, default=None):
        """获取系统设置值

        Args:
            session: 数据库会话
            key: 设置键名
            default: 默认值，如果设置不存在

        Returns:
            str: 设置值
        """
        setting = session.query(cls).filter(cls.key == key).first()
        if not setting:
            return default
        return setting.value

    @classmethod
    def set_setting(cls, session, key, value, description=None):
        """设置系统设置值

        Args:
            session: 数据库会话
            key: 设置键名
            value: 设置值
            description: 设置描述

        Returns:
            SystemSetting: 设置对象
        """
        setting = session.query(cls).filter(cls.key == key).first()
        if not setting:
            setting = cls(key=key, value=value)
            if description:
                setting.description = description
            session.add(setting)
        else:
            setting.value = value
            if description:
                setting.description = description

        session.commit()
        return setting
