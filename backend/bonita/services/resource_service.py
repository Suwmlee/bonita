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
    is_valid_image_file,
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
    def _find_local_upload_file(hash_key: str, preferred_folder: Optional[str] = None) -> str:
        """本地上传 md5 键：在指定目录或 covers/actors 树里找 {hash}.*。"""
        key = (hash_key or "").strip()
        if not key or key.startswith(("http://", "https://")) or os.sep in key or "/" in key:
            return ""

        roots: list[str] = []
        if preferred_folder:
            roots.append(
                os.path.abspath(os.path.join(settings.ASSETS_LOCATION, preferred_folder))
            )
        roots.append(os.path.abspath(os.path.join(settings.ASSETS_LOCATION, COVER_FOLDER)))
        roots.append(
            os.path.abspath(os.path.join(settings.ASSETS_LOCATION, ACTOR_PHOTO_FOLDER))
        )

        seen: set[str] = set()
        for root in roots:
            if not root or root in seen or not os.path.isdir(root):
                continue
            seen.add(root)
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    stem, _ext = os.path.splitext(name)
                    if stem == key or name.startswith(key + "."):
                        fp = os.path.join(dirpath, name)
                        if is_valid_image_file(fp):
                            return fp
        return ""

    @staticmethod
    def _bind_download_path(session: Session, url: str, filepath: str) -> str:
        row = session.query(Downloads).filter(Downloads.url == url).first()
        if row:
            row.filepath = filepath
            session.commit()
        else:
            Downloads(url=url, filepath=filepath).create(session)
        return filepath

    @staticmethod
    def resolve_image_path(
        path: str,
        number: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Optional[str]:
        """供 /resource/image 使用：短会话查库，下载不占用连接池；同 URL 串行避免写坏文件。

        path 可以是：
        - 本地绝对路径
        - 本地上传返回的 md5 键（Downloads.url，无 http）
        - 远程 http(s) URL（可按 number/actor 落到 covers/<番号>/ 或 actors/<名>/）
        """
        if not path:
            return None
        if os.path.isfile(path):
            return path

        is_remote = path.startswith(("http://", "https://"))

        with _resolve_lock_for(path):
            from bonita.db import SessionFactory

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
                if not is_remote:
                    # Downloads 缺失或路径失效时，按 md5 文件名在 assets 里找回
                    found = ResourceService._find_local_upload_file(
                        path, folder if specific else None
                    )
                    if not found:
                        return None
                    if specific:
                        found = (
                            ensure_cached_in_folder(session, path, folder, found)
                            or found
                        )
                    # 已在正确目录时 ensure 不会写库，这里补绑 md5 → filepath
                    ResourceService._bind_download_path(session, path, found)
                    return found
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
                return ResourceService._bind_download_path(session, path, filepath)
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
