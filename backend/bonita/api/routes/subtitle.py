import asyncio
from typing import Any, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.subtitle_service import SubtitleService

router = APIRouter()


def _public(service: SubtitleService, row) -> schemas.SubtitlePublic:
    return schemas.SubtitlePublic.model_validate(service.describe(row))


@router.get("/", response_model=schemas.SubtitleCollection)
def list_subtitles(
    session: SessionDep,
    skip: int = 0,
    limit: int = 50,
    filter: str = None,
    unmatched: bool = False,
    media_item_id: int = None,
) -> Any:
    """字幕列表。media_item_id 为指定媒体项，filter 模糊匹配番号、标题、剧名和文件名。"""
    service = SubtitleService(session)
    rows, count = service.list_subtitles(
        skip=skip,
        limit=limit,
        filter_text=filter,
        unmatched=unmatched,
        media_item_id=media_item_id,
    )
    return schemas.SubtitleCollection(data=[_public(service, row) for row in rows], count=count)


@router.get("/groups", response_model=schemas.SubtitleGroupCollection)
def list_subtitle_groups(
    session: SessionDep,
    skip: int = 0,
    limit: int = 20,
    filter: str = None,
    unmatched: bool = False,
) -> Any:
    """按媒体项分组。单集收到所属剧下面，未关联的单独一组。"""
    service = SubtitleService(session)
    groups, count = service.list_groups(
        skip=skip,
        limit=limit,
        filter_text=filter,
        unmatched=unmatched,
    )
    return schemas.SubtitleGroupCollection(
        data=[schemas.SubtitleGroupPublic.model_validate(group) for group in groups],
        count=count,
    )


@router.post("/upload", response_model=schemas.SubtitleUploadResult)
async def upload_subtitles(
    session: SessionDep,
    files: List[UploadFile] = File(...),
    number: Optional[str] = Form(default=None),
    media_item_id: Optional[int] = Form(default=None),
) -> Any:
    """上传字幕。指定媒体项或番号时按该目标关联，否则从文件名识别番号。电影和剧集不从文件名猜测。"""
    service = SubtitleService(session)
    saved = []
    failed = []
    unmatched = 0
    replaced = 0
    for upload in files:
        content = await upload.read()
        try:
            result = await asyncio.to_thread(
                service.save_bytes,
                upload.filename or "",
                content,
                number,
                media_item_id,
            )
        except ValueError as exc:
            failed.append(str(exc))
            continue
        saved.append(_public(service, result["subtitle"]))
        unmatched += int(result["unmatched"])
        replaced += int(result["replaced"])
    if not saved and failed:
        raise HTTPException(status_code=400, detail=failed[0])
    return schemas.SubtitleUploadResult(data=saved, unmatched=unmatched, replaced=replaced, failed=failed)


@router.post("/deliver", response_model=schemas.SubtitleDeliverResult)
def deliver_subtitles(session: SessionDep, body: schemas.SubtitleDeliverRequest) -> Any:
    """把这些媒体项上的在用字幕复制到转移记录的目标文件旁边。"""
    try:
        result = SubtitleService(session).deliver_items(
            media_item_ids=body.media_item_ids,
            part_number=body.part_number,
            overwrite=body.overwrite,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return schemas.SubtitleDeliverResult(**result)


@router.put("/{subtitle_id}", response_model=schemas.SubtitlePublic)
def update_subtitle(session: SessionDep, subtitle_id: int, body: schemas.SubtitleUpdate) -> Any:
    """修改字幕关联的媒体项或番号，以及语言和部次。"""
    try:
        row = SubtitleService(session).update_subtitle(
            subtitle_id,
            number=body.number,
            language=body.language,
            part_number=body.part_number,
            media_item_id=body.media_item_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not row:
        raise HTTPException(status_code=404, detail="字幕不存在")
    return _public(SubtitleService(session), row)


@router.delete("/{subtitle_id}", response_model=schemas.Response)
def delete_subtitle(session: SessionDep, subtitle_id: int) -> Any:
    if not SubtitleService(session).delete_subtitle(subtitle_id):
        raise HTTPException(status_code=404, detail="字幕不存在")
    return schemas.Response(success=True, message="字幕已删除")


@router.post("/{subtitle_id}/retransfer", response_model=schemas.SubtitleRetransferResult)
def retransfer_subtitle(session: SessionDep, subtitle_id: int) -> Any:
    """重新转移挂着这条在用字幕的记录，重写海报、NFO，并在转移结束时带上字幕。"""
    service = SubtitleService(session)
    row = service.get(subtitle_id)
    if not row:
        raise HTTPException(status_code=404, detail="字幕不存在")
    if not row.media_item_id:
        raise HTTPException(status_code=400, detail="字幕尚未关联媒体项")
    if not row.preferred:
        raise HTTPException(status_code=400, detail="这份不是当前使用的字幕")
    started = service.retransfer_matches(row.media_item_id, row.part_number or 0)
    return schemas.SubtitleRetransferResult(started=started)


@router.post("/{subtitle_id}/prefer", response_model=schemas.SubtitleDeliverResult)
def prefer_subtitle(session: SessionDep, subtitle_id: int) -> Any:
    """改用这一份，清掉原来那份记下的文件，再写到目标旁边。海报和 NFO 由随后的重新转移更新。"""
    try:
        result = SubtitleService(session).use_subtitle(subtitle_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="字幕不存在")
    return schemas.SubtitleDeliverResult(**result)


@router.post("/{subtitle_id}/deliver", response_model=schemas.SubtitleDeliverResult)
def deliver_one_subtitle(session: SessionDep, subtitle_id: int, overwrite: bool = False) -> Any:
    """把当前在用的这一条复制到该媒体项、相同部次的目标文件旁边。"""
    try:
        result = SubtitleService(session).deliver_subtitle(subtitle_id, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="字幕不存在")
    return schemas.SubtitleDeliverResult(**result)
