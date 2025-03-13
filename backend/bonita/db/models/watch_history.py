from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
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
    
    # 来源信息
    source = Column(String, nullable=False, comment="观看历史来源(trakt, emby, jellyfin, douban等)")
    external_id = Column(String, nullable=False, comment="来源系统中的ID")
    
    # 观看信息
    played_at = Column(DateTime, comment="观看时间")
    play_count = Column(Integer, default=1, comment="观看次数")
    play_progress = Column(Float, default=100.0, comment="播放进度百分比")
    duration = Column(Integer, comment="时长(秒)")
    
    # 评分信息
    rating = Column(Float, default=0.0, comment="用户评分(1-10)")
    has_rating = Column(Boolean, default=False, comment="是否有评分")
    
    # 记录信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<WatchHistory {self.source}:{self.external_id}>" 