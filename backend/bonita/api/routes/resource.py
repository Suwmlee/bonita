from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
import os
import hashlib
import logging
from datetime import datetime

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.core.config import settings
from bonita.db.models.metadata import Metadata
from bonita.db.models.downloads import Downloads
from bonita.modules.media_service.emby import EmbyService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/image")
async def get_image_by_query(path: str, session: SessionDep):
    """Get image from local cache or download it using query parameter

    Args:
        path: The image URL (can be non-encoded) or file hash
        session: Database session

    Returns:
        FileResponse: The image file
    """
    cache_downloads_cover = session.query(Downloads).filter(Downloads.url == path).first()
    if not cache_downloads_cover or not os.path.exists(cache_downloads_cover.filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(cache_downloads_cover.filepath)


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    custom_url: str = None,
    session: SessionDep = None
):
    """Upload an image file

    Args:
        file: The image file to upload
        custom_url: Optional custom URL to use instead of file hash
        session: Database session

    Returns:
        dict: Information about the uploaded file
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generate a unique filename using hash of content and original filename
    content = await file.read()
    file_hash = hashlib.md5(content).hexdigest()
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{file_hash}{file_ext}"

    # Ensure cache directory exists
    download_folder = os.path.abspath(os.path.join(settings.CACHE_LOCATION, "images"))
    os.makedirs(download_folder, exist_ok=True)

    # Save file to cache directory
    file_path = os.path.join(download_folder, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # Use custom_url if provided, otherwise use file_hash
    url_value = custom_url if custom_url is not None else file_hash

    # Check if a record with this URL already exists
    existing_download = session.query(Downloads).filter(Downloads.url == url_value).first()

    if existing_download:
        # Update existing record
        existing_download.filepath = file_path
        existing_download.updatetime = datetime.now()
        session.commit()
        download = existing_download
    else:
        # Save to downloads table
        download = Downloads(
            url=url_value,
            filepath=file_path,
            updatetime=datetime.now()
        )
        download.create(session)

    return schemas.Response(success=True, message=url_value)


@router.get("/poster")
async def get_poster(
    title: str,
    imdb_id: str = None,
    tmdb_id: str = None,
    number: str = None,
    session: SessionDep = None
):
    """获取海报图片，根据参数选择不同来源

    Args:
        title: 标题
        imdb_id: IMDB ID
        tmdb_id: TMDB ID
        number: 番号，如果提供则从metadata获取
        session: 数据库会话

    Returns:
        FileResponse或RedirectResponse: 图片文件或重定向到Emby图片URL
    """
    # 如果提供了number，优先从metadata获取cover
    if number:
        try:
            metadata = session.query(Metadata).filter(Metadata.number == number.upper()).first()
            if metadata and metadata.cover:
                # 根据cover字段值从Downloads表获取文件路径
                cache_downloads_cover = session.query(Downloads).filter(Downloads.url == metadata.cover).first()
                if cache_downloads_cover and os.path.exists(cache_downloads_cover.filepath):
                    return FileResponse(cache_downloads_cover.filepath)
        except Exception as e:
            logger.error(f"从metadata获取海报失败: {e}")
            # 记录错误但继续尝试其他方法获取海报
            pass

    # 如果number为空或者从metadata获取失败，尝试从Emby获取
    try:
        emby_service = EmbyService()
        if emby_service.is_initialized:
            poster_url = emby_service.get_poster_url(title, imdb_id, tmdb_id)
            if poster_url:
                return RedirectResponse(poster_url)
    except Exception as e:
        logger.error(f"从Emby获取海报失败: {e}")
        # 记录错误但继续尝试其他方法获取海报
        pass
