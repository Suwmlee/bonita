from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Date, FLOAT, ForeignKey
from sqlalchemy.orm import relationship

from bonita.db import Base


class Metadata(Base):
    """元数据
    存储丰富的媒体详情，特别是特殊影片的详细信息
    """
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联到中央媒体项
    media_item_id = Column(Integer, ForeignKey("mediaitem.id"), index=True)
    media_item = relationship("MediaItem", backref="metadata_detail")
    
    # 基础信息 (已有字段)
    number = Column(String, default="", index=True, comment="番号")
    title = Column(String, default="", nullable=False, comment="标题")
    studio = Column(String, default="", comment="制作公司")
    release = Column(Date, comment="发行日期")
    year = Column(Integer, default=datetime.now().year, comment="发行年份")
    runtime = Column(String, default="", comment="时长")
    genre = Column(String, default="", comment="类型")
    rating = Column(String, default="", comment="评级")
    language = Column(String, default="", comment="语言")
    country = Column(String, default="", comment="国家")
    outline = Column(String, default="", comment="简介")
    director = Column(String, default="", comment="导演")
    actor = Column(String, default="", comment="演员")
    actor_photo = Column(String, default="", comment="演员图片")
    cover = Column(String, default="", comment="封面海报")
    cover_small = Column(String, default="", comment="缩略图")
    extrafanart = Column(String, default="", comment="影片橱窗")
    trailer = Column(String, default="", comment="预告")
    tag = Column(String, default="", comment="标签（用于分类）")
    label = Column(String, default="", comment="标记（用于标记）")
    series = Column(String, default="", comment="系列")
    userrating = Column(FLOAT, default=0.0, comment="用户评分")
    uservotes = Column(Integer, default=0, comment="用户投票数")
    detailurl = Column(String, default="", comment="来源链接")
    site = Column(String, default="", comment="资源站点")
    updatetime = Column(DateTime, default=datetime.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<Metadata {self.number}: {self.title}>"
