from fastapi import APIRouter, HTTPException
from typing import Any, List

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.record_service import RecordService
from bonita.services.subtitle_service import normalize_number, SubtitleService

router = APIRouter()


def _records_public(session, joined_results) -> List[schemas.RecordPublic]:
    pairs = []
    for trans_record, extra_info in joined_results:
        number = extra_info.number if extra_info else ""
        pairs.append((number, trans_record.part_number or 0))
    subtitle_counts = SubtitleService(session).counts_for(pairs)

    record_list = []
    for trans_record, extra_info in joined_results:
        extra_info_public = None
        number = ""
        if extra_info:
            extra_info_public = schemas.ExtraInfoPublic.model_validate(extra_info)
            number = extra_info.number or ""
        subtitle_count = subtitle_counts.get((normalize_number(number), trans_record.part_number or 0), 0)
        record_list.append(schemas.RecordPublic(
            transfer_record=schemas.TransferRecordPublic.model_validate(trans_record),
            extra_info=extra_info_public,
            subtitle_count=subtitle_count,
        ))
    return record_list


@router.get("/all", response_model=schemas.RecordsPublic)
def get_records(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    task_id: int = None,
    search: str = None,
    sort_by: str = "updatetime",
    sort_desc: bool = True
) -> Any:
    """ 获取记录信息 包含 ExtraInfo
    可以根据task_id进行精确过滤
    search参数可同时模糊匹配srcname和srcpath
    sort_by参数可以指定排序字段，默认按updatetime排序
    sort_desc参数可以指定是否降序排序，默认为True
    """
    record_service = RecordService(session)
    joined_results, count = record_service.get_records(
        skip=skip,
        limit=limit,
        task_id=task_id,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc
    )

    return schemas.RecordsPublic(data=_records_public(session, joined_results), count=count)


@router.get("/groups", response_model=schemas.RecordGroupsPublic)
def get_record_groups(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    task_id: int = None,
    search: str = None,
    sort_by: str = "updatetime",
    sort_desc: bool = True
) -> Any:
    """按媒体项返回词条。

    只包含已经挂上 media_item_id 的记录。单集收到父剧。
    搜索命中番号、标题、外部编号、源文件名或源路径时返回整张词条。
    分页单位是词条。sort_by 目前按词条内最新记录的 updatetime 排序。
    """
    groups, count = RecordService(session).get_record_groups(
        skip=skip,
        limit=limit,
        task_id=task_id,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    flat_rows = []
    offsets = []
    for group in groups:
        offsets.append(len(flat_rows))
        flat_rows.extend(group["rows"])
    publics = _records_public(session, flat_rows)
    data = []
    for index, group in enumerate(groups):
        start = offsets[index]
        end = offsets[index + 1] if index + 1 < len(offsets) else len(publics)
        records = publics[start:end]
        data.append(schemas.RecordGroupPublic(
            key=group["key"],
            kind=group["kind"],
            number=group["number"],
            title=group["title"] or "",
            imdb_id=group["imdb_id"] or "",
            tmdb_id=group["tmdb_id"] or "",
            tvdb_id=group["tvdb_id"] or "",
            cover=group["cover"] or "",
            crop=group["crop"],
            record_count=len(records),
            latest_updatetime=group["latest_updatetime"],
            records=records,
        ))
    return schemas.RecordGroupsPublic(data=data, count=count)


@router.put("/record", response_model=schemas.RecordPublic)
def update_record(session: SessionDep, record: schemas.RecordPublic) -> Any:
    """ 更新记录信息 包含 ExtraInfo
    """
    record_service = RecordService(session)
    extra_update = record.extra_info.model_dump(exclude_unset=True) if record.extra_info else None
    transfer_record, extra_info = record_service.update_record_with_extra(
        record_id=record.transfer_record.id,
        transfer_update=record.transfer_record.model_dump(exclude_unset=True),
        extra_update=extra_update,
    )
    if not transfer_record:
        raise HTTPException(status_code=404, detail=f"TransferRecord with id {record.transfer_record.id} not found")

    updated_transfer_record_public = schemas.TransferRecordPublic.model_validate(transfer_record)
    updated_extra_info_public = schemas.ExtraInfoPublic.model_validate(extra_info) if extra_info else None
    return schemas.RecordPublic(transfer_record=updated_transfer_record_public, extra_info=updated_extra_info_public)


@router.put("/update-top-folder", response_model=schemas.Response)
def update_top_folder(
    session: SessionDep,
    srcfolder: str,
    old_top_folder: str,
    new_top_folder: str
) -> Any:
    """更新 top_folder

    更新指定 srcfolder 和 top_folder 相同的所有记录的 top_folder 字段
    """
    record_service = RecordService(session)
    success, message, _ = record_service.update_top_folder(
        srcfolder=srcfolder,
        old_top_folder=old_top_folder,
        new_top_folder=new_top_folder
    )

    return schemas.Response(
        success=success,
        message=message
    )


@router.put("/update-season", response_model=schemas.Response)
def update_season(
    session: SessionDep,
    srcpath: str,
    new_season: int
) -> Any:
    """更新 season

    更新源文件上层目录相同的所有记录的 season 和 isepisode 字段
    """
    record_service = RecordService(session)
    success, message, _ = record_service.update_season(
        srcpath=srcpath,
        new_season=new_season
    )

    return schemas.Response(
        success=success,
        message=message
    )


@router.delete("/records", response_model=schemas.Response)
def delete_records(
    session: SessionDep,
    record_ids: List[int],
    force: bool = False
) -> Any:
    """删除记录信息"""
    record_service = RecordService(session)
    success, message, _, _ = record_service.delete_records(record_ids, force)

    return schemas.Response(
        success=success,
        message=message
    )


@router.get("/transrecords", response_model=schemas.TransferRecordsPublic)
def get_trans_records(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    record_service = RecordService(session)
    trans_records, count = record_service.get_trans_records(skip, limit)

    record_list = [schemas.TransferRecordPublic.model_validate(record) for record in trans_records]
    return schemas.TransferRecordsPublic(data=record_list, count=count)
