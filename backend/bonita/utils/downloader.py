import os
import requests
import hashlib
import mimetypes

from bonita.core.config import settings


def get_file_extension(response):
    """
    根据 HTTP 头中的 Content-Type 获取文件扩展名
    :param response: HTTP 响应对象
    :return: 文件扩展名
    """
    content_type = response.headers.get('Content-Type')
    if content_type:
        return mimetypes.guess_extension(content_type)
    return ''


def generate_file_name(url, response):
    """
    根据 URL 和 HTTP 响应生成文件名
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
    """
    下载文件
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
