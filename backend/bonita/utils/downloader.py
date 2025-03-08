import os
import shutil
import requests
import hashlib
import mimetypes
from sqlalchemy.orm import Session

from bonita.core.config import settings
from bonita.db.models.downloads import Downloads
from bonita.utils.http import get_active_proxy


def get_cached_file(session: Session, url: str, folder) -> str:
    """ 获取缓存图片
    :param session: 数据库会话
    :param url: 下载链接
    :param folder: 下载文件保存的缓存目录
    :return: 缓存的文件路径
    """
    cache_downloads_cover = session.query(Downloads).filter(Downloads.url == url).first()
    # TODO 文件过期
    if not cache_downloads_cover:
        # 数据库中没有记录，下载并添加记录
        # 获取代理设置
        proxy = get_active_proxy(session)
        cache_cover_path = download_file(url, folder, proxy)
        cache_downloads_cover = Downloads(url=url, filepath=cache_cover_path)
        cache_downloads_cover.create(session)
    elif not os.path.exists(cache_downloads_cover.filepath):
        # 数据库有记录但文件不存在，重新下载并更新记录
        proxy = get_active_proxy(session)
        cache_cover_path = download_file(url, folder, proxy)
        cache_downloads_cover.filepath = cache_cover_path
        session.commit()
    return cache_downloads_cover.filepath


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


def get_file_extension(response):
    """ 根据 HTTP 头中的 Content-Type 获取文件扩展名
    :param response: HTTP 响应对象
    :return: 文件扩展名
    """
    content_type = response.headers.get('Content-Type')
    if content_type:
        return mimetypes.guess_extension(content_type)
    return ''


def generate_file_name(url, response):
    """ 根据 URL 和 HTTP 响应生成文件名
    :param url: 下载链接
    :param response: HTTP 响应对象
    :return: 生成的文件名
    """
    file_name = hashlib.md5(url.encode()).hexdigest()
    file_extension = os.path.splitext(url)[1]

    if not file_extension:
        file_extension = get_file_extension(response)

    if not file_extension:
        file_extension = '.jpg'  # 默认扩展名

    return file_name + file_extension


def download_file(url, download_dir, proxy=None):
    """ 下载文件
    :param url: 下载链接
    :param download_dir: 下载文件保存的目录
    :param proxy: 代理信息，格式为 {"http": "http://proxy.com:8080", "https": "http://proxy.com:8080"}
    :return: 下载的文件路径
    """
    # 设置代理
    proxies = proxy if proxy else {}

    # 下载文件
    response = requests.get(url, proxies=proxies, stream=True)
    response.raise_for_status()

    # 生成文件名
    file_name = generate_file_name(url, response)

    # 设置下载路径
    download_folder = os.path.abspath(os.path.join(settings.CACHE_LOCATION, download_dir))
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    download_path = os.path.join(download_folder, file_name)

    # 保存文件
    with open(download_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

    return download_path
