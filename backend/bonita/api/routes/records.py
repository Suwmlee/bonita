from fastapi import APIRouter, HTTPException
from typing import Any, List
from bonita import schemas
from bonita.schemas.record import TransferRecordPublic, TransferRecordsPublic

from bonita.api.deps import SessionDep
from bonita.db.models.record import TransRecords

router = APIRouter()


@router.get("/transrecords", response_model=TransferRecordsPublic)
async def get_trans_records(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    trans_records = session.query(TransRecords).offset(skip).limit(limit).all()
    count = session.query(TransRecords).count()

    record_list = [schemas.TransferRecordPublic.model_validate(record) for record in trans_records]
    return schemas.TransferRecordsPublic(data=record_list, count=count)
