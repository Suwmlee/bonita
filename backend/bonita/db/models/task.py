

from sqlalchemy import Column, Integer, String, Boolean

from bonita.db import Base


class TransferTask(Base):
    """
    转移任务
    """
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default='movie')
    description = Column(String, default='')
    enabled = Column(Boolean, default=True)
    deleted = Column(Boolean, default=True)

    # 任务类型: 1. 移动 2. 不移动,整理?
    task_type = Column(Integer, default=1)
    # 转移类型: 1. 硬链接 2. 移动 3. 复制
    transfer_type = Column(Integer, default=1)
    auto_watch = Column(Boolean, default=False, comment="开启自动监测")
    clean_others = Column(Boolean, default=True, comment="清理其他文件")
    optimize_name = Column(Boolean, default=True, comment="优化名字") 

    # 内容类型: 1. 电影 2. 电视节目
    content_type = Column(Integer, default=1, comment="内容类型")
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
