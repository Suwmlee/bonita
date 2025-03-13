from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from bonita.db import Base


class MediaItem(Base):
    """媒体项目中央映射表
    作为所有媒体内容的统一标识和桥接各种元数据来源
    """
    id = Column(Integer, primary_key=True, index=True)
    
    # 内部标识
    media_type = Column(String, nullable=False, comment="媒体类型: movie, episode, special")
    
    # 外部平台标识映射
    imdb_id = Column(String, index=True, comment="IMDB ID")
    tmdb_id = Column(String, index=True, comment="TMDB ID")
    tvdb_id = Column(String, index=True, comment="TVDB ID")
    douban_id = Column(String, index=True, comment="豆瓣ID")
    
    # 特殊内容标识
    number = Column(String, index=True, comment="番号")
    
    # 基础信息（用于快速显示，减少联表查询）
    title = Column(String, nullable=False, comment="标题")
    original_title = Column(String, comment="原始标题")
    year = Column(Integer, comment="发行年份")
    poster = Column(String, comment="海报图片URL")
    
    # 对于剧集类型
    series_id = Column(Integer, ForeignKey("mediaitem.id"), comment="关联的剧集ID")
    season_number = Column(Integer, default=-1, comment="季数")
    episode_number = Column(Integer, default=-1, comment="集数")
    
    # 记录信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间") 
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关系
    series = relationship("MediaItem", remote_side=[id], backref="episodes")
    
    def __repr__(self):
        return f"<MediaItem {self.title} ({self.year or ''})>" 