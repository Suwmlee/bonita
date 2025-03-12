import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from typing import Any
from sqlalchemy import or_

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.db.models.record import TransRecords
from bonita.db.models.extrainfo import ExtraInfo
from bonita.utils.filehelper import cleanFilebyFilter

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
    query = session.query(TransRecords, ExtraInfo).outerjoin(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath)

    # 添加过滤条件
    if task_id is not None:
        query = query.filter(TransRecords.task_id == task_id)
    if search is not None:
        query = query.filter(
            or_(
                TransRecords.srcname.like(f"%{search}%"),
                TransRecords.srcpath.like(f"%{search}%")
            )
        )

    # 添加排序
    sort_field = getattr(TransRecords, sort_by, TransRecords.updatetime)
    if sort_desc:
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field)

    # 应用分页
    joined_query = query.offset(skip).limit(limit).all()

    record_list = []
    for trans_record, extra_info in joined_query:
        transfer_record_public = schemas.TransferRecordPublic.model_validate(trans_record)
        # 处理 extra_info 为空的情况
        extra_info_public = None
        if extra_info:
            extra_info_public = schemas.ExtraInfoPublic.model_validate(extra_info)
        record_list.append(schemas.RecordPublic(transfer_record=transfer_record_public, extra_info=extra_info_public))

    # 获取总记录数时也要应用过滤条件
    count_query = session.query(TransRecords)
    if task_id is not None:
        count_query = count_query.filter(TransRecords.task_id == task_id)
    if search is not None:
        count_query = count_query.filter(
            or_(
                TransRecords.srcname.like(f"%{search}%"),
                TransRecords.srcpath.like(f"%{search}%")
            )
        )

    count = count_query.count()
    return schemas.RecordsPublic(data=record_list, count=count)


@router.put("/record", response_model=schemas.RecordPublic)
async def update_record(session: SessionDep, record: schemas.RecordPublic) -> Any:
    """ 更新记录信息 包含 ExtraInfo
    """
    result = session.query(TransRecords, ExtraInfo).outerjoin(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath).filter(TransRecords.id == record.transfer_record.id).first()

    if not result or not result[0]:
        raise HTTPException(status_code=404, detail=f"TransferRecord with id {record.transfer_record.id} not found")
    transfer_record: TransRecords = result[0]
    update_dict = record.transfer_record.model_dump(exclude_unset=True)
    transfer_record.update(session, update_dict)
    transfer_record.updatetime = datetime.now()
    extra_info: ExtraInfo = result[1] if result[1] else None
    if extra_info:
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
    # 找到所有匹配的记录
    query = session.query(TransRecords).filter(
        TransRecords.srcfolder == srcfolder,
        TransRecords.top_folder == old_top_folder
    )

    # 获取匹配的记录数
    records_count = query.count()

    if records_count == 0:
        return schemas.Response(
            success=False,
            message=f"没有找到匹配的记录: srcfolder={srcfolder}, top_folder={old_top_folder}"
        )

    # 批量更新记录
    query.update({"top_folder": new_top_folder, "updatetime": datetime.now()})
    session.commit()

    return schemas.Response(
        success=True,
        message=f"成功更新 {records_count} 条记录的 top_folder 从 '{old_top_folder}' 到 '{new_top_folder}'"
    )


@router.delete("/records", response_model=schemas.Response)
async def delete_records(
    session: SessionDep,
    record_ids: list[int],
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

    if not record_ids:
        raise HTTPException(status_code=400, detail="No record IDs provided")

    deleted_count = 0
    failed_ids = []

    for record_id in record_ids:
        record = session.query(TransRecords).filter(TransRecords.id == record_id).first()
        if not record:
            failed_ids.append(record_id)
            continue

        # 默认删除目标路径的文件
        cleanfolder = os.path.dirname(record.destpath)
        namefilter = os.path.splitext(os.path.basename(record.destpath))[0]
        cleanFilebyFilter(cleanfolder, namefilter)
        # 删除关联的额外信息
        extra_info = session.query(ExtraInfo).filter(ExtraInfo.filepath == record.srcpath).first()
        if extra_info:
            session.delete(extra_info)
        if force:
            # 如果强制删除，那么也删除源文件和记录
            cleanfolder = os.path.dirname(record.srcpath)
            namefilter = os.path.splitext(os.path.basename(record.srcpath))[0]
            cleanFilebyFilter(cleanfolder, namefilter)
            session.delete(record)
        else:
            # 清除状态，可以重新转移
            record.top_folder = ''
            record.second_folder = ''
            record.isepisode = False
            record.season = -1
            record.episode = -1
            record.deleted = True
            record.deadtime = datetime.now() + timedelta(days=7)
        deleted_count += 1
    session.commit()

    if failed_ids:
        return schemas.Response(
            success=True if deleted_count > 0 else False,
            message=f"Deleted {deleted_count} records. Failed to delete records with IDs: {failed_ids}"
        )

    return schemas.Response(
        success=True,
        message=f"Successfully deleted {deleted_count} records"
    )


@router.get("/transrecords", response_model=schemas.TransferRecordsPublic)
async def get_trans_records(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    trans_records = session.query(TransRecords).offset(skip).limit(limit).all()
    count = session.query(TransRecords).count()

    record_list = [schemas.TransferRecordPublic.model_validate(record) for record in trans_records]
    return schemas.TransferRecordsPublic(data=record_list, count=count)
