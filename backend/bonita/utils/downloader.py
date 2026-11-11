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

from bonita.core.config import settings
from bonita.db.models.downloads import Downloads
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


def is_valid_image_file(filepath: str) -> bool:
    """粗检本地文件是否为可用图片（排除空文件/HTML 错误页）。"""
    if not filepath or not os.path.isfile(filepath):
        return False
    try:
        size = os.path.getsize(filepath)
    except OSError:
        return False
    if size < 24:
        return False
    try:
        with open(filepath, "rb") as f:
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


def cached_filepath(session: Session, url: str) -> str:
    """已缓存且文件仍有效则返回路径，否则空串（不改库）。"""
    if not url:
        return ""
    cache = session.query(Downloads).filter(Downloads.url == url).first()
    if cache and is_valid_image_file(cache.filepath or ""):
        return cache.filepath
    return ""


def _assets_folder_abs(folder: str) -> str:
    return os.path.abspath(os.path.join(settings.ASSETS_LOCATION, folder or ""))


def _path_under_folder(filepath: str, folder: str) -> bool:
    """判断绝对路径是否落在 ASSETS/<folder>/ 下（含子文件）。"""
    if not filepath or not folder:
        return False
    target = _assets_folder_abs(folder)
    try:
        return os.path.commonpath([os.path.abspath(filepath), target]) == target
    except ValueError:
        return False


def ensure_cached_in_folder(session: Session, url: str, folder: str, filepath: str) -> str:
    """已有本地文件时，若未在目标子目录则搬迁并回写 Downloads。"""
    if not filepath or not is_valid_image_file(filepath):
        return ""
    if _path_under_folder(filepath, folder):
        return filepath

    target_dir = _assets_folder_abs(folder)
    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.basename(filepath)
    if not filename:
        ext = os.path.splitext(filepath)[1] or ".jpg"
        filename = hashlib.md5((url or filepath).encode()).hexdigest() + ext
    dest = os.path.join(target_dir, filename)
    if os.path.abspath(filepath) != os.path.abspath(dest):
        if os.path.exists(dest):
            # 目标已有同名，保留目标，删掉错位源文件
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
            except OSError:
                pass
        else:
            shutil.move(filepath, dest)
        filepath = dest

    cache = session.query(Downloads).filter(Downloads.url == url).first() if url else None
    if cache:
        cache.filepath = filepath
        session.commit()
    elif url:
        Downloads(url=url, filepath=filepath).create(session)
    return filepath


def _is_specific_assets_folder(folder: str) -> bool:
    """covers/<番号>、actors/<名> 为明确子目录；裸 covers/actors 不算。"""
    parts = [p for p in (folder or "").replace("\\", "/").split("/") if p]
    return len(parts) >= 2


def process_cached_file(session: Session, url: str, folder) -> str:
    """获取缓存图片；folder 为相对 ASSETS 的子目录，如 covers/<番号>、actors/<名>。

    若已缓存但目录不对（例如预览时落到裸 covers/），会搬到 folder 下。
    目标若是裸 covers/actors，只下载不搬迁，避免冲掉已归档文件。
    """
    folder = folder or ""
    cached = cached_filepath(session, url)
    if cached:
        if _is_specific_assets_folder(folder):
            return ensure_cached_in_folder(session, url, folder, cached) or cached
        return cached
    filepath = download_file(url, folder, get_active_proxy(session))
    cache = session.query(Downloads).filter(Downloads.url == url).first()
    if cache:
        cache.filepath = filepath
        session.commit()
    else:
        cache = Downloads(url=url, filepath=filepath)
        cache.create(session)
    return cache.filepath


def update_cache_from_local(session: Session, source_path: str, folder: str, url: str):
    """根据本地文件更新缓存记录；folder 为相对 ASSETS 的子目录。"""
    cache_downloads = session.query(Downloads).filter(Downloads.url == url).first()
    if cache_downloads and is_valid_image_file(cache_downloads.filepath or ""):
        if _is_specific_assets_folder(folder):
            return ensure_cached_in_folder(
                session, url, folder, cache_downloads.filepath
            ) or cache_downloads.filepath
        return cache_downloads.filepath

    cache_folder = _assets_folder_abs(folder)
    os.makedirs(cache_folder, exist_ok=True)
    file_extension = os.path.splitext(source_path)[1] or ".jpg"
    file_name = hashlib.md5(url.encode()).hexdigest() + file_extension
    cache_path = os.path.join(cache_folder, file_name)
    if os.path.exists(source_path):
        shutil.copy2(source_path, cache_path)

    if cache_downloads:
        cache_downloads.filepath = cache_path
        session.commit()
    else:
        cache_downloads = Downloads(url=url, filepath=cache_path)
        session.add(cache_downloads)
        session.commit()

    return cache_path


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
    """下载文件到 ASSETS（download_dir 如 covers/<番号>）。"""
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
                download_folder = os.path.abspath(
                    os.path.join(settings.ASSETS_LOCATION, download_dir)
                )
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
