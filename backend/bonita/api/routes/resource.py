import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.services.resource_service import ResourceService

router = APIRouter()


@router.get("/image")
async def get_image_by_query(path: str):
    """按 URL/路径取图。下载远程图时不长时间占用 DB 连接，避免演员墙并发打满连接池。"""
    filepath = await asyncio.to_thread(ResourceService.resolve_image_path, path)
    if not filepath:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        filepath,
        headers={"Cache-Control": "private, max-age=0, must-revalidate"},
    )


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    custom_url: str = None,
    number: str = None,
    actor: str = None,
    session: SessionDep = None
):
    """Upload an image file。传 actor 时落到 actors/<名>/。"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    content = await file.read()
    url_value = ResourceService(session).save_image(
        content,
        file.filename,
        custom_url,
        number=number,
        actor=actor,
    )
    return schemas.Response(success=True, message=url_value)


@router.get("/poster")
async def get_poster(
    title: str = "",
    imdb_id: str = None,
    tmdb_id: str = None,
    number: str = None,
    external_id: str = None,
    source: str = SOURCE_EMBY,
    image_tag: str = None,
    session: SessionDep = None
):
    """获取海报图片。有番号时返回完整的 metadata.cover。"""
    result = ResourceService(session).get_poster(
        title=title,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id,
        number=number,
        external_id=external_id,
        source=source,
        image_tag=image_tag,
    )
    if not result:
        return None
    if result.kind == "file":
        return FileResponse(
            result.path,
            headers={"Cache-Control": result.cache_control},
        )
    response = RedirectResponse(result.path, status_code=302)
    response.headers["Cache-Control"] = result.cache_control
    return response
