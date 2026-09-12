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


def process_cached_file(session: Session, url: str, folder) -> str:
    """ 获取缓存图片
    :param session: 数据库会话
    :param url: 下载链接
    :param folder: 下载文件保存的缓存目录
    :return: 缓存的文件路径
    """
    cache = session.query(Downloads).filter(Downloads.url == url).first()
    if cache and os.path.exists(cache.filepath):
        return cache.filepath
    filepath = download_file(url, folder, get_active_proxy(session))
    if cache:
        cache.filepath = filepath
        session.commit()
    else:
        cache = Downloads(url=url, filepath=filepath)
        cache.create(session)
    return cache.filepath


def update_cache_from_local(session: Session, source_path: str, folder: str, url: str):
    """ 根据本地文件更新缓存记录
    :param session: 数据库会话
    :param source_path: 源文件路径
    :param folder: 文件保存的缓存目录
    :param url: 文件链接或标识符
    """
    # 检查数据库中是否已有记录
    cache_downloads = session.query(Downloads).filter(Downloads.url == url).first()
    # 如果有记录，且文件存在，则跳过
    if cache_downloads and os.path.exists(cache_downloads.filepath):
        return cache_downloads.filepath
    # 确保缓存目录存在
    cache_folder = os.path.abspath(os.path.join(settings.CACHE_LOCATION, folder))
    os.makedirs(cache_folder, exist_ok=True)
    # 生成文件名
    file_extension = os.path.splitext(source_path)[1]
    if not file_extension:
        file_extension = '.jpg'  # 默认扩展名
    file_name = hashlib.md5(url.encode()).hexdigest() + file_extension
    cache_path = os.path.join(cache_folder, file_name)
    # 复制文件到缓存目录
    if os.path.exists(source_path):
        shutil.copy2(source_path, cache_path)

    # 更新或创建数据库记录
    if cache_downloads:
        cache_downloads.filepath = cache_path
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
    """ 下载文件
    :param url: 下载链接
    :param download_dir: 下载文件保存的目录
    :param proxy: 代理信息，格式为 {"http": "http://proxy.com:8080", "https": "http://proxy.com:8080"}
    :return: 下载的文件路径
    """
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
                download_folder = os.path.abspath(os.path.join(settings.CACHE_LOCATION, download_dir))
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
            return download_path
        except (requests.RequestException, OSError) as e:
            status = getattr(getattr(e, 'response', None), 'status_code', None)
            if attempt >= DOWNLOAD_RETRIES or (status and status < 500 and status != 429):
                raise
            logger.warning(f"下载失败 (尝试 {attempt}/{DOWNLOAD_RETRIES}): {url} — {e}")
            time.sleep(attempt)
