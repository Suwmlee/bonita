

from sqlalchemy import Column, Integer, String, Boolean

from app.db import Base


class TransferTask(Base):
    """
    媒体库表
    task_type:
    1. 移动
    2. 整理?

    link_type:
    :1  硬链接
    :2  移动文件
    """
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default='movie')
    description = Column(String, default='')
    task_type = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    auto_watch = Column(Boolean, default=False, comment="开启自动监测")

    transfer_type = Column(Integer, default=1)
    source_folder = Column(String, default='/media')
    output_folder = Column(String, default='/media/output')
    failed_folder = Column(String, default='/media/failed')

    escape_folder = Column(String, default='Sample,sample')
    escape_literals = Column(String, default="\\()/")
    escape_size = Column(Integer, default=0)
    threads_num = Column(Integer, default=5)

    # 仅在刮削模式下生效,刮削配置
    sc_enabled = Column(Boolean, default=False, comment="启用刮削")
    sc_id = Column(Integer, default=0, comment="使用的刮削配置")
