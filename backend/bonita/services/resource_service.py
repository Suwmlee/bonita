import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from bonita.core.config import settings
from bonita.db.models.downloads import Downloads
from bonita.db.models.metadata import Metadata
from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.modules.media_service.factory import get_media_client

logger = logging.getLogger(__name__)


@dataclass
class PosterResult:
    kind: str
    path: str
    cache_control: str


class ResourceService:
    """缓存图片、上传与海报解析。"""

    def __init__(self, session: Session):
        self.session = session

    def get_cached_image_path(self, path: str) -> Optional[str]:
        cache_downloads_cover = self.session.query(Downloads).filter(Downloads.url == path).first()
        if not cache_downloads_cover or not os.path.exists(cache_downloads_cover.filepath):
            return None
        return cache_downloads_cover.filepath

    def save_image(self, content: bytes, filename: Optional[str], custom_url: Optional[str] = None) -> str:
        file_hash = hashlib.md5(content).hexdigest()
        file_ext = os.path.splitext(filename or "")[1]
        stored_name = f"{file_hash}{file_ext}"
        download_folder = os.path.abspath(os.path.join(settings.CACHE_LOCATION, "images"))
        os.makedirs(download_folder, exist_ok=True)
        file_path = os.path.join(download_folder, stored_name)
        with open(file_path, "wb") as f:
            f.write(content)

        url_value = custom_url if custom_url is not None else file_hash
        existing_download = self.session.query(Downloads).filter(Downloads.url == url_value).first()
        if existing_download:
            existing_download.filepath = file_path
            self.session.commit()
        else:
            download = Downloads(
                url=url_value,
                filepath=file_path,
                updatetime=datetime.now()
            )
            download.create(self.session)
        return url_value

    def get_poster(
        self,
        title: str = "",
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[str] = None,
        number: Optional[str] = None,
        emby_id: Optional[str] = None,
        external_id: Optional[str] = None,
        source: str = SOURCE_EMBY,
        image_tag: Optional[str] = None,
    ) -> Optional[PosterResult]:
        remote_id = external_id or emby_id
        if remote_id:
            try:
                client = get_media_client(source)
                if client:
                    poster_url = client.get_item_image_url(remote_id, image_tag)
                    if poster_url:
                        return PosterResult(kind="redirect", path=poster_url, cache_control="no-store")
            except Exception as e:
                logger.error(f"从媒体服务器获取海报失败: {e}")

        if number:
            try:
                metadata = (
                    self.session.query(Metadata)
                    .filter(func.upper(Metadata.number) == number.upper())
                    .first()
                )
                if metadata and metadata.cover:
                    cache_downloads_cover = (
                        self.session.query(Downloads)
                        .filter(Downloads.url == metadata.cover)
                        .first()
                    )
                    if cache_downloads_cover and os.path.exists(cache_downloads_cover.filepath):
                        return PosterResult(
                            kind="file",
                            path=cache_downloads_cover.filepath,
                            cache_control="public, max-age=0, must-revalidate",
                        )
            except Exception as e:
                logger.error(f"从metadata获取海报失败: {e}")

        try:
            client = get_media_client(source)
            if client:
                poster_url = client.get_poster_url(title, imdb_id, tmdb_id)
                if poster_url:
                    return PosterResult(kind="redirect", path=poster_url, cache_control="no-store")
        except Exception as e:
            logger.error(f"从媒体服务器获取海报失败: {e}")
        return None
