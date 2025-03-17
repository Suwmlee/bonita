from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship

from bonita.db import Base


class WatchHistory(Base):
    """观看历史
    仅关注用户的观看行为，不再存储媒体元数据
    """
    id = Column(Integer, primary_key=True, index=True)

    # 关联到中央媒体项
    media_item_id = Column(Integer, ForeignKey("mediaitem.id"), nullable=False, index=True)
    media_item = relationship("MediaItem", backref="watchhistory")

    # 观看信息
    watched = Column(Boolean, default=False, server_default="0", comment="是否观看")
    watch_count = Column(Integer, default=1, comment="观看次数")
    play_progress = Column(Float, default=100.0, comment="播放进度百分比")
    duration = Column(Integer, comment="时长(秒)")

    favorite = Column(Boolean, default=False, comment="是否喜爱")
    has_rating = Column(Boolean, default=False, comment="是否有评分")
    rating = Column(Float, default=0.0, comment="用户评分(1-10)")

    createtime = Column(DateTime, default=func.now(), server_default=func.now(), comment="创建时间")
    updatetime = Column(DateTime, default=func.now(), onupdate=func.now(), server_default=func.now(), comment="更新时间")
