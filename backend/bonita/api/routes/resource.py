from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import hashlib
from datetime import datetime

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.core.config import settings
from bonita.utils.downloader import process_cached_file
from bonita.db.models.downloads import Downloads

router = APIRouter()


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
