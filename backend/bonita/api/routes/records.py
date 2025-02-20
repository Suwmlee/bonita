from fastapi import APIRouter, HTTPException
from typing import Any, List

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.db.models.record import TransRecords
from bonita.db.models.extrainfo import ExtraInfo

router = APIRouter()


@router.get("/all", response_model=schemas.RecordsPublic)
async def get_records(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """ 获取记录信息 包含 ExtraInfo
    """
    joined_query = session.query(TransRecords, ExtraInfo).outerjoin(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath).offset(skip).limit(limit).all()
    record_list = []
    for trans_record, extra_info in joined_query:
        transfer_record_public = schemas.TransferRecordPublic.model_validate(trans_record)
        extra_info_public = schemas.ExtraInfoPublic.model_validate(extra_info) if extra_info else None
        record_list.append(schemas.RecordPublic(transfer_record=transfer_record_public, extra_info=extra_info_public))

    count = session.query(TransRecords).count()
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
    extra_info: ExtraInfo = result[1] if result[1] else None
    if extra_info:
        extra_info_update_dict = record.extra_info.model_dump(exclude_unset=True)
        extra_info.update(session, extra_info_update_dict)

    session.commit()
    updated_transfer_record_public = schemas.TransferRecordPublic.model_validate(transfer_record)
    updated_extra_info_public = schemas.ExtraInfoPublic.model_validate(extra_info) if extra_info else None
    return schemas.RecordPublic(transfer_record=updated_transfer_record_public, extra_info=updated_extra_info_public)


@router.get("/transrecords", response_model=schemas.TransferRecordsPublic)
async def get_trans_records(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    trans_records = session.query(TransRecords).offset(skip).limit(limit).all()
    count = session.query(TransRecords).count()

    record_list = [schemas.TransferRecordPublic.model_validate(record) for record in trans_records]
    return schemas.TransferRecordsPublic(data=record_list, count=count)
