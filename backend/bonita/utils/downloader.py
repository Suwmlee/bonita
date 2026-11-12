import hashlib
import logging
import mimetypes
import os
import shutil
import time
from urllib.parse import urlparse

import requests
from PIL import Image
from sqlalchemy.orm import Session

from bonita.db.models.downloads import ImageCache
from bonita.utils.assets import (
    assets_folder_abs,
    content_hash_from_key,
    is_specific_assets_folder,
    local_image_key,
    path_under_folder,
    require_specific_assets_folder,
    resolve_write_folder,
    to_abs_path,
    to_stored_path,
)
from bonita.utils.http import get_active_proxy

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = (10, 30)
DOWNLOAD_RETRIES = 3
DOWNLOAD_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


_IMAGE_MAGIC = (
    b"\xff\xd8\xff",  # jpeg
    b"\x89PNG\r\n\x1a\n",  # png
    b"GIF87a",
    b"GIF89a",
    b"RIFF",  # webp 容器，下面再看 WEBP
)


def cache_lookup_keys(url: str) -> list[str]:
    """同一逻辑图可能对应 local:<md5> 与历史裸 md5。"""
    text = (url or "").strip()
    if not text:
        return []
    keys = [text]
    digest = content_hash_from_key(text)
    if digest:
        for alt in (local_image_key(digest), digest):
            if alt not in keys:
                keys.append(alt)
    return keys


def is_valid_image_file(filepath: str) -> bool:
    """粗检本地文件是否为可用图片（排除空文件/HTML 错误页）。"""
    abs_path = to_abs_path(filepath) if filepath and not os.path.isabs(filepath) else filepath
    if not abs_path or not os.path.isfile(abs_path):
        return False
    try:
        size = os.path.getsize(abs_path)
    except OSError:
        return False
    if size < 24:
        return False
    try:
        with open(abs_path, "rb") as f:
            head = f.read(16)
    except OSError:
        return False
    if head.startswith(b"<") or head[:4].lower() == b"<!do" or b"html" in head.lower():
        return False
    if any(head.startswith(m) for m in _IMAGE_MAGIC):
        if head.startswith(b"RIFF") and head[8:12] != b"WEBP":
            return False
        return True
    return False


def _bind_filepath(session: Session, url: str, abs_filepath: str) -> str:
    """把绝对路径以相对形式写入 ImageCache，返回绝对路径。"""
    stored = to_stored_path(abs_filepath)
    keys = cache_lookup_keys(url)
    cache = (
        session.query(ImageCache).filter(ImageCache.url.in_(keys)).first()
        if keys
        else None
    )
    if cache:
        if cache.url != url and url:
            cache.url = url
        cache.filepath = stored
        session.commit()
    elif url:
        ImageCache(url=url, filepath=stored).create(session)
    return to_abs_path(stored)


def cached_filepath(session: Session, url: str) -> str:
    """已缓存且文件仍有效则返回绝对路径，否则空串（不改库）。"""
    keys = cache_lookup_keys(url)
    if not keys:
        return ""
    cache = session.query(ImageCache).filter(ImageCache.url.in_(keys)).first()
    if not cache:
        return ""
    abs_path = to_abs_path(cache.filepath or "")
    if is_valid_image_file(abs_path):
        return abs_path
    return ""


def ensure_cached_in_folder(session: Session, url: str, folder: str, filepath: str) -> str:
    """已有本地文件时，若未在目标子目录则搬迁并回写 ImageCache（仅明确归档目录）。"""
    require_specific_assets_folder(folder)
    abs_path = to_abs_path(filepath) if filepath else ""
    if not abs_path or not is_valid_image_file(abs_path):
        return ""
    if path_under_folder(abs_path, folder):
        return _bind_filepath(session, url, abs_path) if url else abs_path

    target_dir = assets_folder_abs(folder)
    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.basename(abs_path)
    if not filename:
        ext = os.path.splitext(abs_path)[1] or ".jpg"
        filename = hashlib.md5((url or abs_path).encode()).hexdigest() + ext
    dest = os.path.join(target_dir, filename)
    if os.path.abspath(abs_path) != os.path.abspath(dest):
        if os.path.exists(dest):
            try:
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
            except OSError:
                pass
        else:
            shutil.move(abs_path, dest)
        abs_path = dest

    return _bind_filepath(session, url, abs_path) if url else abs_path


def process_cached_file(session: Session, url: str, folder) -> str:
    """获取缓存图片。

    folder 为明确子目录时：命中可从 cache/ 搬迁归档；未命中则下载到该目录。
    folder 不明确时：下载/命中落在 cache/，不搬迁到裸 covers/actors。
    """
    target = resolve_write_folder(folder)
    cached = cached_filepath(session, url)
    if cached:
        if is_specific_assets_folder(target):
            return ensure_cached_in_folder(session, url, target, cached) or cached
        return cached

    filepath = download_file(url, target, get_active_proxy(session))
    return _bind_filepath(session, url, filepath)


def update_cache_from_local(session: Session, source_path: str, folder: str, url: str):
    """根据本地文件更新缓存记录；无明确目录时写入 cache/。"""
    target = resolve_write_folder(folder)
    existing = cached_filepath(session, url)
    if existing:
        if is_specific_assets_folder(target):
            return ensure_cached_in_folder(session, url, target, existing) or existing
        return existing

    cache_folder = assets_folder_abs(target)
    os.makedirs(cache_folder, exist_ok=True)
    file_extension = os.path.splitext(source_path)[1] or ".jpg"
    file_name = hashlib.md5(url.encode()).hexdigest() + file_extension
    cache_path = os.path.join(cache_folder, file_name)
    if os.path.exists(source_path):
        shutil.copy2(source_path, cache_path)

    return _bind_filepath(session, url, cache_path)


def _convert_gif_to_jpg(gif_path: str) -> str:
    """ 将 GIF 文件转换为 JPG，取第一帧，删除原 GIF 文件
    :return: 转换后的 JPG 文件路径
    """
    jpg_path = os.path.splitext(gif_path)[0] + '.jpg'
    img = Image.open(gif_path)
    img.seek(0)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.save(jpg_path, 'JPEG', quality=95)
    img.close()
    os.remove(gif_path)
    return jpg_path


def get_file_extension(response):
    """ 根据 HTTP 头中的 Content-Type 获取文件扩展名
    :param response: HTTP 响应对象
    :return: 文件扩展名
    """
    content_type = (response.headers.get('Content-Type') or '').split(';')[0].strip().lower()
    if not content_type:
        return ''
    if content_type in ('image/jpeg', 'image/jpg'):
        return '.jpg'
    return mimetypes.guess_extension(content_type) or ''


def generate_file_name(url, response):
    """ 根据 URL 和 HTTP 响应生成文件名
    :param url: 下载链接
    :param response: HTTP 响应对象
    :return: 生成的文件名
    """
    file_name = hashlib.md5(url.encode()).hexdigest()
    file_extension = os.path.splitext(urlparse(url).path)[1] or get_file_extension(response) or '.jpg'
    return file_name + file_extension


def download_file(url, download_dir, proxy=None):
    """下载文件到 ASSETS。

    download_dir 须为 covers/<番号>、actors/<名> 或 cache/（否则落到 cache/）。
    """
    download_dir = resolve_write_folder(download_dir)
    parsed = urlparse(url)
    headers = {"User-Agent": DOWNLOAD_USER_AGENT}
    if parsed.scheme and parsed.netloc:
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            with requests.get(
                url,
                proxies=proxy or {},
                headers=headers,
                stream=True,
                timeout=DOWNLOAD_TIMEOUT,
            ) as response:
                response.raise_for_status()
                file_name = generate_file_name(url, response)
                download_folder = assets_folder_abs(download_dir)
                os.makedirs(download_folder, exist_ok=True)
                download_path = os.path.join(download_folder, file_name)
                with open(download_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)

            if os.path.getsize(download_path) == 0:
                os.remove(download_path)
                raise IOError(f"Downloaded empty file: {url}")
            if download_path.lower().endswith('.gif'):
                download_path = _convert_gif_to_jpg(download_path)
            if not is_valid_image_file(download_path):
                try:
                    os.remove(download_path)
                except OSError:
                    pass
                raise IOError(f"Downloaded content is not an image: {url}")
            return download_path
        except (requests.RequestException, OSError) as e:
            status = getattr(getattr(e, 'response', None), 'status_code', None)
            if attempt >= DOWNLOAD_RETRIES or (status and status < 500 and status != 429):
                raise
            logger.warning(f"下载失败 (尝试 {attempt}/{DOWNLOAD_RETRIES}): {url} — {e}")
            time.sleep(attempt)
