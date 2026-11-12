
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from bonita.db import Base


class ImageCache(Base):
    """图片资产缓存索引（非 BT 下载列表）。

    表名仍为 downloads（历史兼容）。filepath 存相对 ASSETS_LOCATION 的路径。
    url 为逻辑键：远程 http(s) URL，或本地上传 `local:<md5>`（兼容旧的裸 md5）。
    """
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False, comment="逻辑键：远程 URL 或 local:<md5>")
    filepath = Column(String, nullable=False, comment="相对 ASSETS 的文件路径")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


# 兼容旧导入名
Downloads = ImageCache
