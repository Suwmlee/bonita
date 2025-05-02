from fastapi import APIRouter, HTTPException
from typing import Any, List

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.record_service import RecordService

router = APIRouter()


@router.get("/all", response_model=schemas.RecordsPublic)
async def get_records(
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

    record_list = []
    for trans_record, extra_info in joined_results:
        transfer_record_public = schemas.TransferRecordPublic.model_validate(trans_record)
        # 处理 extra_info 为空的情况
        extra_info_public = None
        if extra_info:
            extra_info_public = schemas.ExtraInfoPublic.model_validate(extra_info)
        record_list.append(schemas.RecordPublic(transfer_record=transfer_record_public, extra_info=extra_info_public))

    return schemas.RecordsPublic(data=record_list, count=count)


@router.put("/record", response_model=schemas.RecordPublic)
async def update_record(session: SessionDep, record: schemas.RecordPublic) -> Any:
    """ 更新记录信息 包含 ExtraInfo
    """
    record_service = RecordService(session)
    transfer_record, extra_info = record_service.get_record_by_id(record.transfer_record.id)
    if not transfer_record:
        raise HTTPException(status_code=404, detail=f"TransferRecord with id {record.transfer_record.id} not found")

    update_dict = record.transfer_record.model_dump(exclude_unset=True)
    transfer_record.update(session, update_dict)
    if extra_info and record.extra_info:
        extra_info_update_dict = record.extra_info.model_dump(exclude_unset=True)
        extra_info.update(session, extra_info_update_dict)
    session.commit()

    updated_transfer_record_public = schemas.TransferRecordPublic.model_validate(transfer_record)
    updated_extra_info_public = schemas.ExtraInfoPublic.model_validate(extra_info) if extra_info else None
    return schemas.RecordPublic(transfer_record=updated_transfer_record_public, extra_info=updated_extra_info_public)


@router.put("/update-top-folder", response_model=schemas.Response)
async def update_top_folder(
    session: SessionDep,
    srcfolder: str,
    old_top_folder: str,
    new_top_folder: str
) -> Any:
    """更新 top_folder

    更新指定 srcfolder 和 top_folder 相同的所有记录的 top_folder 字段

    Args:
        session: 数据库会话
        srcfolder: 源文件夹路径
        old_top_folder: 原来的 top_folder 值
        new_top_folder: 新的 top_folder 值

    Returns:
        更新操作的结果
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


@router.delete("/records", response_model=schemas.Response)
async def delete_records(
    session: SessionDep,
    record_ids: List[int],
    force: bool = False
) -> Any:
    """删除记录信息

    Args:
        session: 数据库会话
        record_ids: 要删除的记录ID列表
        force: 是否强制删除，如果为True则同时删除关联的文件

    Returns:
        删除操作的结果
    """
    record_service = RecordService(session)
    success, message, _, _ = record_service.delete_records(record_ids, force)

    return schemas.Response(
        success=success,
        message=message
    )


@router.get("/transrecords", response_model=schemas.TransferRecordsPublic)
async def get_trans_records(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    record_service = RecordService(session)
    trans_records, count = record_service.get_trans_records(skip, limit)

    record_list = [schemas.TransferRecordPublic.model_validate(record) for record in trans_records]
    return schemas.TransferRecordsPublic(data=record_list, count=count)
