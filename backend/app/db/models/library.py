

from sqlalchemy import Column, Integer, String, Boolean
from app.core.db import Base


class Library(Base):
    """
    媒体库表
    lib_mode:
    1. 仅移动
    2. 移动并且刮削

    link_type:
    :1  移动文件
    :2  硬链接
    """
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default='movie')
    description = Column(String, default='')
    lib_type = Column(Integer, default=1)
    is_enabled = Column(Boolean, default=True)
    auto_watch = Column(Boolean, default=False)

    link_type = Column(Integer, default=1)
    source_folder = Column(String, default='/media')
    output_folder = Column(String, default='/media/output')
    failed_folder = Column(String, default='/media/failed')

    escape_folder = Column(String, default='Sample,sample')
    escape_literals = Column(String, default="\()/")
    escape_size = Column(Integer, default=0)

    # 仅在刮削模式下生效,刮削配置
    lib_scid = Column(String, default="")
    threads_num = Column(Integer, default=5)
