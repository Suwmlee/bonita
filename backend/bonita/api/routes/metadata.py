from fastapi import APIRouter, HTTPException
from typing import Any

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.metadata_service import MetadataService

router = APIRouter()


@router.post("/", response_model=schemas.MetadataPublic)
async def create_metadata(
    session: SessionDep,
    metadata_in: schemas.MetadataCreate
) -> Any:
    """创建新元数据"""
    db_metadata = MetadataService(session).create_metadata(metadata_in.model_dump())
    return schemas.MetadataPublic.model_validate(db_metadata.to_dict())


@router.get("/all", response_model=schemas.MetadataCollection)
async def get_metadata(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    filter: str = None,
    sort_by: str = "updatetime",
    sort_desc: bool = True
) -> Any:
    """ 获取元数据
    支持使用 filter 参数对 number 和 actor 同时进行模糊搜索
    sort_by参数可以指定排序字段，默认按updatetime排序
    sort_desc参数可以指定是否降序排序，默认为True
    """
    data, count = MetadataService(session).list_metadata(
        skip=skip,
        limit=limit,
        filter_text=filter,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    data_list = [schemas.MetadataPublic.model_validate(meta.to_dict()) for meta in data]
    return schemas.MetadataCollection(data=data_list, count=count)


@router.put("/{id}", response_model=schemas.MetadataPublic)
async def update_metadata(
    session: SessionDep,
    id: int,
    metadata: schemas.MetadataBase
) -> Any:
    """更新元数据"""
    db_metadata = MetadataService(session).update_metadata(
        id, metadata.model_dump(exclude_unset=True)
    )
    if not db_metadata:
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")
    return schemas.MetadataPublic.model_validate(db_metadata.to_dict())


@router.delete("/{id}", response_model=schemas.Response)
async def delete_metadata(
    session: SessionDep,
    id: int
) -> Any:
    """删除元数据"""
    if not MetadataService(session).delete_metadata(id):
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")
    return schemas.Response(success=True, message="Metadata deleted successfully")
