

from datetime import datetime
from sqlalchemy import Column, Integer, String, Date

from bonita.db import Base


class Metadata(Base):
    """ 元数据
    """
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, default="", nullable=False, comment="番号")
    title = Column(String, default="", nullable=False, comment="标题")
    studio = Column(String, default="", comment="制作公司")
    release = Column(Date, comment="发行日期")
    year = Column(Integer, default=datetime.now().year, comment="发行年份")
    duration = Column(Integer, default=0, comment="时长（分钟）")
    genre = Column(String, default="", comment="类型")
    rating = Column(String, default="", comment="评级")
    language = Column(String, default="", comment="语言")
    country = Column(String, default="", comment="国家")
    outline = Column(String, default="", comment="简介")
    director = Column(String, default="", comment="导演")
    actor = Column(String, default="", comment="演员")
    actor_photo = Column(String, default="", comment="演员图片")
    cover = Column(String, default="", nullable=False, comment="封面海报")
    cover_small = Column(String, default="", comment="缩略图")
    extrafanart = Column(String, default="", comment="影片橱窗")
    trailer = Column(String, default="", comment="预告")
    tag = Column(String, default="", comment="标签（用于分类）")
    label = Column(String, default="", comment="标记（用于标记）")
    series = Column(String, default="", comment="系列")
    userrating = Column(String, default="", comment="用户评分")
    uservotes = Column(String, default="", comment="用户投票数")
    detailurl = Column(String, default="", comment="来源链接")
    site = Column(String, default="", comment="资源站点")
