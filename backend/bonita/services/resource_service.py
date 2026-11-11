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
from bonita.utils.downloader import (
    cached_filepath,
    download_file,
    ensure_cached_in_folder,
    process_cached_file,
)
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


def actor_folder_for_name(name: Optional[str]) -> str:
    safe = _safe_dirname(name)
    return os.path.join(ACTOR_PHOTO_FOLDER, safe) if safe else ACTOR_PHOTO_FOLDER


class ResourceService:
    """缓存图片、上传与海报解析。"""

    def __init__(self, session: Session):
        self.session = session

    def _folder_for_url(
        self,
        url: str,
        *,
        number: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> str:
        """落盘目录：优先用调用方传入的 actor/number；否则按 URL 反查。"""
        if (actor or "").strip():
            return actor_folder_for_name(actor)
        if (number or "").strip():
            return cover_folder_for_number(number)
        row_actor = self.session.query(Actor.name).filter(Actor.photo == url).first()
        if row_actor and row_actor.name:
            return actor_folder_for_name(row_actor.name)
        row = (
            self.session.query(Metadata.number)
            .filter((Metadata.cover == url) | (Metadata.cover_small == url))
            .order_by(Metadata.id.desc())
            .first()
        )
        return cover_folder_for_number(row.number if row else None)

    @staticmethod
    def resolve_image_path(
        path: str,
        number: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Optional[str]:
        """供 /resource/image 使用：短会话查库，下载不占用连接池；同 URL 串行避免写坏文件。

        预览尚未入库的封面/头像时，必须传 number 或 actor，否则会落到裸 covers/。
        """
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
                folder = ResourceService(session)._folder_for_url(
                    path, number=number, actor=actor
                )
                # 仅在有明确子目录时搬迁；裸 covers/ 不当作目标，避免冲掉已正确归档的文件
                specific = folder not in (COVER_FOLDER, ACTOR_PHOTO_FOLDER)
                cached = cached_filepath(session, path)
                if cached:
                    if specific:
                        relocated = ensure_cached_in_folder(
                            session, path, folder, cached
                        )
                        return relocated or cached
                    return cached
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

    def cache_remote_image(
        self,
        url: str,
        *,
        number: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> str:
        """主动按 actor/number 缓存远程图到正确子目录（保存头像/封面时用）。"""
        text = (url or "").strip()
        if not text.startswith(("http://", "https://")):
            return ""
        folder = self._folder_for_url(text, number=number, actor=actor)
        try:
            return process_cached_file(self.session, text, folder)
        except Exception as e:
            logger.warning("Failed to cache remote image %s → %s: %s", text, folder, e)
            return ""

    def relocate_actor_photo_dir(self, old_name: str, new_name: str) -> int:
        """改主名后：actors/<旧>/ → actors/<新>/，并回写 Downloads.filepath。"""
        old_folder = actor_folder_for_name(old_name)
        new_folder = actor_folder_for_name(new_name)
        if old_folder == new_folder:
            return 0
        old_abs = os.path.abspath(os.path.join(settings.ASSETS_LOCATION, old_folder))
        new_abs = os.path.abspath(os.path.join(settings.ASSETS_LOCATION, new_folder))
        if not os.path.isdir(old_abs):
            return 0
        os.makedirs(new_abs, exist_ok=True)
        moved = 0
        mapping: Dict[str, str] = {}
        for name in os.listdir(old_abs):
            src = os.path.join(old_abs, name)
            if not os.path.isfile(src):
                continue
            dest = os.path.join(new_abs, name)
            if os.path.exists(dest):
                try:
                    os.remove(src)
                except OSError:
                    pass
            else:
                os.rename(src, dest)
            mapping[os.path.abspath(src)] = dest
            mapping[name] = dest
        if mapping:
            prefix = old_abs.rstrip(os.sep) + os.sep
            rows = (
                self.session.query(Downloads)
                .filter(Downloads.filepath.like(prefix + "%"))
                .all()
            )
            for row in rows:
                key = os.path.abspath(row.filepath or "")
                dest = mapping.get(key) or mapping.get(os.path.basename(row.filepath or ""))
                if dest:
                    row.filepath = dest
                    moved += 1
        try:
            if os.path.isdir(old_abs) and not os.listdir(old_abs):
                os.rmdir(old_abs)
        except OSError:
            pass
        if moved:
            self.session.flush()
        return moved

    def save_image(
        self,
        content: bytes,
        filename: Optional[str],
        custom_url: Optional[str] = None,
        *,
        number: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> str:
        file_hash = hashlib.md5(content).hexdigest()
        file_ext = os.path.splitext(filename or "")[1]
        stored_name = f"{file_hash}{file_ext}"
        relative_folder = (
            actor_folder_for_name(actor)
            if (actor or "").strip()
            else cover_folder_for_number(number)
        )
        download_folder = os.path.abspath(
            os.path.join(settings.ASSETS_LOCATION, relative_folder)
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
