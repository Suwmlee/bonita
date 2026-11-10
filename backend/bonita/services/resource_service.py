import hashlib
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from bonita.core.config import settings
from bonita.db.models.actor import Actor
from bonita.db.models.downloads import Downloads
from bonita.db.models.metadata import Metadata
from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.modules.media_service.factory import ensure_media_client
from bonita.utils.downloader import cached_filepath, download_file
from bonita.utils.http import get_active_proxy

logger = logging.getLogger(__name__)

COVER_FOLDER = "covers"
ACTOR_PHOTO_FOLDER = "actors"
_DIR_FORBIDDEN = '<>:"/\\|?*'
_resolve_locks_guard = threading.Lock()
_resolve_locks: Dict[str, threading.Lock] = {}


def _resolve_lock_for(url: str) -> threading.Lock:
    with _resolve_locks_guard:
        lock = _resolve_locks.get(url)
        if lock is None:
            lock = threading.Lock()
            _resolve_locks[url] = lock
        return lock


@dataclass
class PosterResult:
    kind: str
    path: str
    cache_control: str


def _safe_dirname(name: Optional[str]) -> str:
    """番号/演员名作目录名：去掉路径非法字符；空则返回空串。"""
    text = (name or "").strip()
    for ch in _DIR_FORBIDDEN:
        text = text.replace(ch, "_")
    return text.strip(" .")


def cover_folder_for_number(number: Optional[str]) -> str:
    name = _safe_dirname(number)
    return os.path.join(COVER_FOLDER, name) if name else COVER_FOLDER


class ResourceService:
    """缓存图片、上传与海报解析。"""

    def __init__(self, session: Session):
        self.session = session

    def _folder_for_url(self, url: str) -> str:
        """按 URL 反查落盘目录：演员头像 actors/<名>/，否则 covers/<番号>/（无番号则 covers）。"""
        actor = self.session.query(Actor.name).filter(Actor.photo == url).first()
        if actor and actor.name:
            return os.path.join(ACTOR_PHOTO_FOLDER, _safe_dirname(actor.name))
        row = (
            self.session.query(Metadata.number)
            .filter((Metadata.cover == url) | (Metadata.cover_small == url))
            .order_by(Metadata.id.desc())
            .first()
        )
        return cover_folder_for_number(row.number if row else None)

    @staticmethod
    def resolve_image_path(path: str) -> Optional[str]:
        """供 /resource/image 使用：短会话查库，下载不占用连接池；同 URL 串行避免写坏文件。"""
        if not path:
            return None
        if os.path.isfile(path):
            return path
        if not path.startswith(("http://", "https://")):
            return None

        with _resolve_lock_for(path):
            from bonita.db import SessionFactory

            proxy = None
            folder = COVER_FOLDER
            session = SessionFactory()
            try:
                cached = cached_filepath(session, path)
                if cached:
                    return cached
                folder = ResourceService(session)._folder_for_url(path)
                proxy = get_active_proxy(session)
            finally:
                session.close()

            try:
                filepath = download_file(path, folder, proxy)
            except Exception as e:
                logger.warning("Failed to fetch remote image %s: %s", path, e)
                return None

            session = SessionFactory()
            try:
                row = session.query(Downloads).filter(Downloads.url == path).first()
                if row:
                    row.filepath = filepath
                    session.commit()
                else:
                    Downloads(url=path, filepath=filepath).create(session)
                return filepath
            finally:
                session.close()

    def save_image(
        self,
        content: bytes,
        filename: Optional[str],
        custom_url: Optional[str] = None,
        *,
        number: Optional[str] = None,
    ) -> str:
        file_hash = hashlib.md5(content).hexdigest()
        file_ext = os.path.splitext(filename or "")[1]
        stored_name = f"{file_hash}{file_ext}"
        download_folder = os.path.abspath(
            os.path.join(settings.ASSETS_LOCATION, cover_folder_for_number(number))
        )
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
        external_id: Optional[str] = None,
        source: str = SOURCE_EMBY,
        image_tag: Optional[str] = None,
    ) -> Optional[PosterResult]:
        if external_id:
            try:
                client = ensure_media_client(source)
                if client:
                    poster_url = client.get_item_image_url(external_id, image_tag)
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
            client = ensure_media_client(source)
            if client:
                poster_url = client.get_poster_url(title, imdb_id, tmdb_id)
                if poster_url:
                    return PosterResult(kind="redirect", path=poster_url, cache_control="no-store")
        except Exception as e:
            logger.error(f"从媒体服务器获取海报失败: {e}")
        return None
