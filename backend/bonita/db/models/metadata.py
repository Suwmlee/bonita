

from sqlalchemy import Column, Integer, String, Boolean

from bonita.db import Base


class Metadata(Base):
    """ 元数据
    """
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, default="编号")
    title = Column(String, default='标题')
    studio = Column(String, default="工作室")
    release = Column(String, default="发布日期")
    year = Column(String, default="年份")
    outline = Column(String, default="概述")
    director = Column(String, default="导演")
    actor = Column(String, default="演员")
    actor_photo = Column(String, default="演员图片")
    cover = Column(String, default="封面")
    cover_small = Column(String, default="缩略图")
    extrafanart = Column(String, default="影片橱窗")
    trailer = Column(String, default="预告")
    tag = Column(String, default="")
    label = Column(String, default="")
    series = Column(String, default="系列")
    userrating = Column(String, default="评分")
    uservotes = Column(String, default="投票数")
    detailurl = Column(String, default="详情链接")
    site = Column(String, default="使用的资源网站")
