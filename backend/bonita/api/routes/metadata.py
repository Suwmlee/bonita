
from fastapi import APIRouter
from typing import Any

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.db.models.metadata import Metadata

router = APIRouter()


@router.get("/all", response_model=schemas.MetadataCollection)
async def get_metadata(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """ 获取元数据
    """
    data = session.query(Metadata).offset(skip).limit(limit).all()
    count = session.query(Metadata).count()

    data_list = [schemas.MetadataPublic.model_validate(meta.to_dict()) for meta in data]
    return schemas.MetadataCollection(data=data_list, count=count)
