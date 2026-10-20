import asyncio
from typing import Any, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.subtitle_service import SubtitleService

router = APIRouter()


def _public(row) -> schemas.SubtitlePublic:
    return schemas.SubtitlePublic.model_validate(row.to_dict())


@router.get("/", response_model=schemas.SubtitleCollection)
def list_subtitles(
    session: SessionDep,
    skip: int = 0,
    limit: int = 50,
    filter: str = None,
    number: str = None,
    unmatched: bool = False,
) -> Any:
    """字幕列表。number 为精确番号，filter 模糊匹配番号和文件名。"""
    rows, count = SubtitleService(session).list_subtitles(
        skip=skip,
        limit=limit,
        filter_text=filter,
        number=number,
        unmatched=unmatched,
    )
    return schemas.SubtitleCollection(data=[_public(row) for row in rows], count=count)


@router.post("/upload", response_model=schemas.SubtitleUploadResult)
async def upload_subtitles(
    session: SessionDep,
    files: List[UploadFile] = File(...),
    number: Optional[str] = Form(default=None),
) -> Any:
    """上传字幕。指定番号时全部关联到该番号，否则从文件名识别。"""
    service = SubtitleService(session)
    saved = []
    failed = []
    unmatched = 0
    replaced = 0
    for upload in files:
        content = await upload.read()
        try:
            result = await asyncio.to_thread(service.save_bytes, upload.filename or "", content, number)
        except ValueError as exc:
            failed.append(str(exc))
            continue
        saved.append(_public(result["subtitle"]))
        unmatched += int(result["unmatched"])
        replaced += int(result["replaced"])
    if not saved and failed:
        raise HTTPException(status_code=400, detail=failed[0])
    return schemas.SubtitleUploadResult(data=saved, unmatched=unmatched, replaced=replaced, failed=failed)


@router.post("/deliver", response_model=schemas.SubtitleDeliverResult)
def deliver_subtitles(session: SessionDep, body: schemas.SubtitleDeliverRequest) -> Any:
    """把该番号已关联的字幕复制到转移记录的目标文件旁边。"""
    try:
        result = SubtitleService(session).deliver_number(
            number=body.number,
            part_number=body.part_number,
            overwrite=body.overwrite,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return schemas.SubtitleDeliverResult(**result)


@router.put("/{subtitle_id}", response_model=schemas.SubtitlePublic)
def update_subtitle(session: SessionDep, subtitle_id: int, body: schemas.SubtitleUpdate) -> Any:
    """修改字幕的番号、语言和部次。"""
    try:
        row = SubtitleService(session).update_subtitle(
            subtitle_id,
            identity_key=body.identity_key,
            language=body.language,
            part_number=body.part_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not row:
        raise HTTPException(status_code=404, detail="字幕不存在")
    return _public(row)


@router.delete("/{subtitle_id}", response_model=schemas.Response)
def delete_subtitle(session: SessionDep, subtitle_id: int) -> Any:
    if not SubtitleService(session).delete_subtitle(subtitle_id):
        raise HTTPException(status_code=404, detail="字幕不存在")
    return schemas.Response(success=True, message="字幕已删除")


@router.post("/{subtitle_id}/deliver", response_model=schemas.SubtitleDeliverResult)
def deliver_one_subtitle(session: SessionDep, subtitle_id: int, overwrite: bool = False) -> Any:
    """把一条字幕复制到匹配番号和部次的目标文件旁边。"""
    try:
        result = SubtitleService(session).deliver_subtitle(subtitle_id, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="字幕不存在")
    return schemas.SubtitleDeliverResult(**result)
