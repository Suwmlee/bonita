
from datetime import datetime
from sqlalchemy import Column, Enum, Integer, String, Boolean, DateTime, Float, Text

from bonita.db import Base
from bonita.utils.filehelper import OperationMethod
from bonita.core.enums import TaskStatus


class TransferConfig(Base):
    """
    转移任务配置
    """
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default='movie')
    description = Column(String, default='')
    enabled = Column(Boolean, default=True)
    deleted = Column(Boolean, default=True)

    operation = Column(Enum(OperationMethod), default=OperationMethod.HARD_LINK)
    auto_watch = Column(Boolean, default=False, comment="开启自动监测")
    clean_others = Column(Boolean, default=True, comment="清理其他文件")
    optimize_name = Column(Boolean, default=True, comment="优化名字")

    # 内容类型: 1. 电影 2. 电视节目
    content_type = Column(Integer, default=1, comment="内容类型")
    source_folder = Column(String, default='/media/source')
    output_folder = Column(String, default='/media/output')
    failed_folder = Column(String, default='/media/failed')
    escape_folder = Column(String, default='Sample,sample,@eaDir')
    escape_literals = Column(String, default="\\()/")
    escape_size = Column(Integer, default=0)
    threads_num = Column(Integer, default=5)

    # 仅在刮削模式下生效,刮削配置
    sc_enabled = Column(Boolean, default=False, comment="启用刮削")
    sc_id = Column(Integer, default=0, comment="使用的刮削配置")


class CeleryTask(Base):
    """
    Celery任务管理表
    """
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, comment="Celery任务ID")
    task_type = Column(String, default="", comment="任务类型")
    detail = Column(String, default="", comment="任务详情")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态")
    progress = Column(Float, default=0.0, comment="进度百分比 (0-100)")
    step = Column(String, default="", comment="当前步骤描述")
    result = Column(String, comment="任务结果")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
