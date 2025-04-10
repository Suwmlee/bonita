from fastapi import APIRouter, HTTPException
from typing import Any
from datetime import datetime

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.db.models.metadata import Metadata
from bonita.utils.downloader import process_cached_file

router = APIRouter()


@router.post("/", response_model=schemas.MetadataPublic)
async def create_metadata(
    session: SessionDep,
    metadata_in: schemas.MetadataCreate
) -> Any:
    """创建新元数据

    Args:
        session: 数据库会话
        metadata_in: 元数据内容

    Returns:
        创建的元数据
    """
    metadata_dict = metadata_in.model_dump()
    if metadata_dict.get("cover") and metadata_dict["cover"].startswith(("http://", "https://")):
        metadata_dict["cover"] = process_cached_file(session, metadata_dict["cover"], metadata_dict["number"])

    db_metadata = Metadata(**metadata_dict)
    db_metadata.create(session)
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
    query = session.query(Metadata)

    # Apply fuzzy search filter if provided
    if filter:
        query = query.filter(
            Metadata.number.ilike(f"%{filter}%") |
            Metadata.actor.ilike(f"%{filter}%")
        )

    # Apply sorting
    sort_column = getattr(Metadata, sort_by, Metadata.updatetime)
    query = query.order_by(sort_column.desc() if sort_desc else sort_column.asc())

    # Get total count after applying filters
    count = query.count()

    # Get paginated data
    data = query.offset(skip).limit(limit).all()

    data_list = [schemas.MetadataPublic.model_validate(meta.to_dict()) for meta in data]
    return schemas.MetadataCollection(data=data_list, count=count)


@router.put("/{id}", response_model=schemas.MetadataPublic)
async def update_metadata(
    session: SessionDep,
    id: int,
    metadata: schemas.MetadataBase
) -> Any:
    """更新元数据

    Args:
        session: 数据库会话
        id: 元数据ID
        metadata: 更新的元数据内容

    Returns:
        更新后的元数据
    """
    db_metadata = session.get(Metadata, id)
    if not db_metadata:
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")

    update_dict = metadata.model_dump(exclude_unset=True)
    if update_dict.get("cover") and update_dict["cover"].startswith(("http://", "https://")):
        update_dict["cover"] = process_cached_file(session, update_dict["cover"], update_dict["number"])

    db_metadata.update(session, update_dict)
    db_metadata.updatetime = datetime.now()
    session.commit()
    session.refresh(db_metadata)
    return schemas.MetadataPublic.model_validate(db_metadata.to_dict())


@router.delete("/{id}", response_model=schemas.Response)
async def delete_metadata(
    session: SessionDep,
    id: int
) -> Any:
    """删除元数据

    Args:
        session: 数据库会话
        id: 元数据ID
    """

    db_metadata = session.get(Metadata, id)
    if not db_metadata:
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")

    session.delete(db_metadata)
    session.commit()
    return schemas.Response(success=True, message="Metadata deleted successfully")
