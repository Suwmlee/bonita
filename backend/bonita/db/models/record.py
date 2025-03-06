
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from bonita.db import Base


class TransRecords(Base):
    """ 转移记录
    ignored: 忽略
    locked: 锁定, 不再进行重命名等
    deleted: 实际内容已经删除
    """
    id = Column(Integer, primary_key=True)
    srcname = Column(String, default='')
    srcpath = Column(String, default='')
    srcfolder = Column(String, default='')
    task_id = Column(Integer, default=0, server_default='0', comment='任务ID')

    ignored = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False, comment='实际目标路径文件已经删除')

    forced_name = Column(String, default='', comment='forced name')
    top_folder = Column(String, default='')
    # 电影类，次级目录;如果是剧集则以season为准
    second_folder = Column(String, default='')
    isepisode = Column(Boolean, default=False)
    season = Column(Integer, default=-1)
    episode = Column(Integer, default=-1)
    # 链接使用的地址，可能与docker内地址不同
    linkpath = Column(String, default='')
    destpath = Column(String, default='')

    updatetime = Column(DateTime, default=datetime.now(), comment="更新时间")
    # 完全删除时间，包括源文件和目标路径文件
    deadtime = Column(DateTime, default=None, comment='time to delete files')
