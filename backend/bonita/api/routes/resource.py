import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse, RedirectResponse

from bonita import schemas
from bonita.api.deps import SessionDep, verify_token
from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.services.resource_service import ResourceService
router = APIRouter()


@router.get("/image")
async def get_image_by_query(
    path: str,
    number: str = None,
    actor: str = None,
):
    """按逻辑键取图；未缓存的远程 URL 会懒下载。

    有 number/actor（或可反查）→ covers/<番号>/ 或 actors/<名>/；
    否则 → assets/cache/（临时区，提交/带 hint 后再归档）。
    """
    filepath = await asyncio.to_thread(
        ResourceService.resolve_image_path, path, number, actor
    )
    if not filepath:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        filepath,
        headers={"Cache-Control": "private, max-age=0, must-revalidate"},
    )


@router.post("/upload/image", dependencies=[Depends(verify_token)])
async def upload_image(
    file: UploadFile = File(...),
    custom_url: str = None,
    number: str = None,
    actor: str = None,
    session: SessionDep = None
):
    """上传图片（需登录）。有 number/actor 则归档；否则落到 assets/cache/。

    返回逻辑键 local:<content_md5>（custom_url 已忽略，保留参数兼容旧客户端）。
    """
    if not file.content_type or not file.content_type.startswith("image/"):
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
    """海报展示解析器（不落盘到 assets）。

    优先媒体库图片 URL（302），其次已缓存的 Metadata.cover 本地文件；
    不负责下载或写入 ASSETS。
    """
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
