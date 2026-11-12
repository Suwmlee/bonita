import hashlib
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from bonita.db.models.actor import Actor
from bonita.db.models.downloads import ImageCache
from bonita.db.models.metadata import Metadata
from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.modules.media_service.factory import ensure_media_client
from bonita.utils.assets import (
    ACTOR_PHOTO_FOLDER,
    CACHE_FOLDER,
    COVER_FOLDER,
    AssetsFolderError,
    assets_folder_abs,
    content_hash_from_key,
    is_remote_image_key,
    is_specific_assets_folder,
    local_image_key,
    normalize_rel,
    resolve_write_folder,
    to_abs_path,
    to_stored_path,
)
from bonita.utils.downloader import (
    cache_lookup_keys,
    cached_filepath,
    download_file,
    ensure_cached_in_folder,
    is_valid_image_file,
    process_cached_file,
)
from bonita.utils.http import get_active_proxy

logger = logging.getLogger(__name__)

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
        """本地上传键：按内容 md5 在 covers/actors 树里找 {hash}.*。"""
        digest = content_hash_from_key(hash_key)
        if not digest:
            return ""

        roots: list[str] = []
        if preferred_folder:
            roots.append(assets_folder_abs(preferred_folder))
        roots.append(assets_folder_abs(COVER_FOLDER))
        roots.append(assets_folder_abs(ACTOR_PHOTO_FOLDER))
        roots.append(assets_folder_abs(CACHE_FOLDER))

        seen: set[str] = set()
        for root in roots:
            if not root or root in seen or not os.path.isdir(root):
                continue
            seen.add(root)
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    stem, _ext = os.path.splitext(name)
                    if stem == digest or name.startswith(digest + "."):
                        fp = os.path.join(dirpath, name)
                        if is_valid_image_file(fp):
                            return fp
        return ""

    @staticmethod
    def _bind_download_path(session: Session, url: str, filepath: str) -> str:
        stored = to_stored_path(filepath)
        keys = cache_lookup_keys(url)
        row = (
            session.query(ImageCache).filter(ImageCache.url.in_(keys)).first()
            if keys
            else None
        )
        if row:
            row.url = url
            row.filepath = stored
            session.commit()
        else:
            ImageCache(url=url, filepath=stored).create(session)
        return to_abs_path(stored)

    @staticmethod
    def resolve_image_path(
        path: str,
        number: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Optional[str]:
        """供 GET /resource/image：懒加载取图。

        - 已缓存：有明确 number/actor 时可从 cache/ 搬迁到 covers|actors
        - 远程未缓存：有明确目录则下到 covers/<番号>/ 或 actors/<名>/；
          否则下到 cache/（临时预览，提交后再归档）
        - 本地 local:<md5>：扫盘找回并补绑索引
        """
        if not path:
            return None
        if os.path.isfile(path):
            return path

        is_remote = is_remote_image_key(path)

        with _resolve_lock_for(path):
            from bonita.db import SessionFactory

            write_folder = CACHE_FOLDER
            proxy = None
            session = SessionFactory()
            try:
                folder = ResourceService(session)._folder_for_url(
                    path, number=number, actor=actor
                )
                write_folder = resolve_write_folder(folder)
                specific = is_specific_assets_folder(write_folder)
                cached = cached_filepath(session, path)
                if cached:
                    if specific:
                        try:
                            return (
                                ensure_cached_in_folder(
                                    session, path, write_folder, cached
                                )
                                or cached
                            )
                        except AssetsFolderError:
                            return cached
                    return cached

                if not is_remote:
                    found = ResourceService._find_local_upload_file(
                        path, write_folder if specific else None
                    )
                    if not found:
                        return None
                    if specific:
                        try:
                            found = (
                                ensure_cached_in_folder(
                                    session, path, write_folder, found
                                )
                                or found
                            )
                        except AssetsFolderError:
                            pass
                    bind_key = path
                    digest = content_hash_from_key(path)
                    if digest and not path.startswith("local:"):
                        bind_key = local_image_key(digest)
                    return ResourceService._bind_download_path(session, bind_key, found)

                proxy = get_active_proxy(session)
            finally:
                session.close()

            try:
                filepath = download_file(path, write_folder, proxy)
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
        """缓存远程图：有 actor/number 归档；否则落到 cache/。"""
        text = (url or "").strip()
        if not text.startswith(("http://", "https://")):
            return ""
        folder = self._folder_for_url(text, number=number, actor=actor)
        try:
            return process_cached_file(self.session, text, folder)
        except AssetsFolderError as e:
            logger.warning("跳过缓存 %s → %s: %s", text, folder, e)
            return ""
        except Exception as e:
            logger.warning("Failed to cache remote image %s → %s: %s", text, folder, e)
            return ""

    def relocate_actor_photo_dir(self, old_name: str, new_name: str) -> int:
        """改主名后：actors/<旧>/ → actors/<新>/，并回写 ImageCache.filepath（相对路径）。"""
        old_folder = actor_folder_for_name(old_name)
        new_folder = actor_folder_for_name(new_name)
        if old_folder == new_folder:
            return 0
        if not is_specific_assets_folder(old_folder) or not is_specific_assets_folder(
            new_folder
        ):
            return 0
        old_abs = assets_folder_abs(old_folder)
        new_abs = assets_folder_abs(new_folder)
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
            mapping[normalize_rel(os.path.join(old_folder, name))] = dest
        if mapping:
            rel_prefix = normalize_rel(old_folder) + "/"
            abs_prefix = old_abs.rstrip(os.sep) + os.sep
            rows = (
                self.session.query(ImageCache)
                .filter(
                    or_(
                        ImageCache.filepath.like(rel_prefix + "%"),
                        ImageCache.filepath.like(abs_prefix + "%"),
                    )
                )
                .all()
            )
            for row in rows:
                stored = row.filepath or ""
                abs_key = os.path.abspath(to_abs_path(stored))
                dest = (
                    mapping.get(abs_key)
                    or mapping.get(normalize_rel(stored))
                    or mapping.get(os.path.basename(stored))
                )
                if dest:
                    row.filepath = to_stored_path(dest)
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
        """上传图片。逻辑键固定为 local:<content_md5>（忽略 custom_url，保留参数兼容旧前端）。

        有 actor/number → actors/<名>/ 或 covers/<番号>/；否则 → cache/。
        """
        if custom_url:
            logger.debug("save_image 忽略 custom_url=%s，改用 local:<md5>", custom_url)
        file_hash = hashlib.md5(content).hexdigest()
        file_ext = os.path.splitext(filename or "")[1]
        stored_name = f"{file_hash}{file_ext}"
        relative_folder = resolve_write_folder(
            actor_folder_for_name(actor)
            if (actor or "").strip()
            else cover_folder_for_number(number)
        )
        download_folder = assets_folder_abs(relative_folder)
        os.makedirs(download_folder, exist_ok=True)
        file_path = os.path.join(download_folder, stored_name)
        with open(file_path, "wb") as f:
            f.write(content)

        url_value = local_image_key(file_hash)
        stored = to_stored_path(file_path)
        keys = cache_lookup_keys(url_value)
        existing = (
            self.session.query(ImageCache).filter(ImageCache.url.in_(keys)).first()
        )
        if existing:
            existing.url = url_value
            existing.filepath = stored
            self.session.commit()
        else:
            ImageCache(
                url=url_value,
                filepath=stored,
                updatetime=datetime.now(),
            ).create(self.session)
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
                    abs_path = cached_filepath(self.session, metadata.cover)
                    if abs_path:
                        return PosterResult(
                            kind="file",
                            path=abs_path,
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
