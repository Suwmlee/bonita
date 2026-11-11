import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any, List, Optional

from scrapinglib import getSupportedSources

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.metadata_service import MetadataService
from bonita.utils.http import get_active_proxy

router = APIRouter()


@router.post("/", response_model=schemas.MetadataPublic)
async def create_metadata(
    session: SessionDep,
    metadata_in: schemas.MetadataCreate
) -> Any:
    """创建新元数据"""
    db_metadata = MetadataService(session).create_metadata(metadata_in.model_dump())
    return schemas.MetadataPublic.model_validate(db_metadata.to_dict())


@router.get("/sites", response_model=List[str])
async def list_metadata_sites() -> Any:
    """获取 scrapinglib 支持的站点列表"""
    sources = getSupportedSources() or ""
    return [s.strip() for s in sources.split(",") if s.strip()]


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


@router.get("/actors", response_model=schemas.ActorCollection)
async def list_actors(
    session: SessionDep,
    skip: int = 0,
    limit: int = 24,
    filter: Optional[str] = None,
    sort: str = "count",
) -> Any:
    """按 Actor 表聚合作品。sort 为 count_desc、count_asc、name_asc、name_desc，佚名固定在最后。"""
    data, count = MetadataService(session).list_actors(
        skip=skip,
        limit=limit,
        filter_text=filter,
        sort=sort,
    )
    return schemas.ActorCollection(data=data, count=count)


@router.post("/actors/sync", response_model=schemas.Response)
async def sync_actors_from_metadata(session: SessionDep) -> Any:
    """从现有 Metadata.actor 回填 Actor / ActorAlias / metadata_actor。"""
    from bonita.services.actor_service import ActorService

    result = ActorService(session).sync_from_metadata(cleanup_orphans=False)
    return schemas.Response(success=True, message="演员回填完成", data=result)


@router.get("/actors/works", response_model=schemas.MetadataCollection)
async def list_actor_works(
    session: SessionDep,
    actor: str = "",
    actor_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 24,
    filter: Optional[str] = None,
) -> Any:
    """获取某一位演员的作品，按更新时间倒序。优先 actor_id。"""
    data, count = MetadataService(session).list_actor_works(
        actor_name=actor,
        skip=skip,
        limit=limit,
        filter_text=filter,
        actor_id=actor_id,
    )
    data_list = [schemas.MetadataPublic.model_validate(meta.to_dict()) for meta in data]
    return schemas.MetadataCollection(data=data_list, count=count)


@router.get("/actors/homonyms", response_model=List[schemas.ActorHomonymPublic])
async def list_actor_homonyms(session: SessionDep, name: str = "") -> Any:
    """按名字列出全部同名演员（含别名命中）。"""
    from bonita.services.actor_service import ActorService

    return ActorService(session).list_homonyms(name)


@router.get("/actors/{actor_id}", response_model=schemas.ActorPublic)
async def get_actor(session: SessionDep, actor_id: int) -> Any:
    """获取演员详情（含别名）。"""
    from bonita.services.actor_service import ActorService

    actor = ActorService(session).get_by_id(actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor with id {actor_id} not found")
    return schemas.ActorPublic.model_validate(actor)


@router.put("/actors/{actor_id}", response_model=schemas.ActorPublic)
async def update_actor(
    session: SessionDep,
    actor_id: int,
    actor_in: schemas.ActorUpdate,
) -> Any:
    """更新演员主名和/或别名。改主名后按出演回写相关 Metadata.actor。"""
    from bonita.services.actor_service import ActorService

    service = ActorService(session)
    actor = service.get_by_id(actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor with id {actor_id} not found")

    try:
        old_name = actor.name
        if actor_in.name is not None and actor_in.name.strip() != actor.name:
            actor = service.rename_actor(actor_id, actor_in.name)
        if actor_in.aliases is not None:
            aliases = list(actor_in.aliases)
            # 同请求改主名时，前端别名列表不含旧主名；保留为别名，避免被覆盖删除
            if (actor.name or "").casefold() != (old_name or "").casefold():
                old_key = (old_name or "").casefold()
                if not any((item or "").casefold() == old_key for item in aliases):
                    aliases.insert(0, old_name)
            actor = service.set_aliases(actor_id, aliases)
        if actor_in.photo is not None:
            actor.photo = actor_in.photo
        if actor_in.birth_date is not None:
            actor.birth_date = actor_in.birth_date
        if actor_in.outline is not None:
            actor.outline = actor_in.outline
        session.commit()
        actor = service.get_by_id(actor_id)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return schemas.ActorPublic.model_validate(actor)


@router.get("/{id}/credits", response_model=List[schemas.MetadataCreditPublic])
async def list_metadata_credits(session: SessionDep, id: int) -> Any:
    """某片出演行（按行，含同名人数）。"""
    from bonita.services.actor_service import ActorService

    if not MetadataService(session).get_by_id(id):
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")
    return ActorService(session).list_credits_for_metadata(id)


@router.put("/{id}/credits/{actor_id}", response_model=List[schemas.MetadataCreditPublic])
async def rematch_metadata_credit(
    session: SessionDep,
    id: int,
    actor_id: int,
    body: schemas.CreditRematchRequest,
) -> Any:
    """只改挂这一行出演到已有演员。"""
    from bonita.services.actor_service import ActorService

    if not MetadataService(session).get_by_id(id):
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")
    try:
        credits = ActorService(session).rematch_credit(id, actor_id, body.to_actor_id)
        session.commit()
        return credits
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{id}/credits/{actor_id}/split", response_model=schemas.CreditSplitResult)
async def split_metadata_credit(
    session: SessionDep,
    id: int,
    actor_id: int,
    body: Optional[schemas.CreditSplitRequest] = None,
) -> Any:
    """新建同名演员，只改挂这一行。"""
    from bonita.services.actor_service import ActorService

    if not MetadataService(session).get_by_id(id):
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")
    payload = body or schemas.CreditSplitRequest()
    try:
        result = ActorService(session).split_credit_to_new_actor(
            id, actor_id, new_name=payload.name
        )
        new_id = result["actor"].id
        session.commit()
        actor = ActorService(session).get_by_id(new_id)
        return schemas.CreditSplitResult(
            actor=schemas.ActorPublic.model_validate(actor),
            credits=result["credits"],
        )
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{id}/refresh", response_model=schemas.MetadataBase)
async def refresh_metadata(
    session: SessionDep,
    id: int,
    params: schemas.MetadataRefreshParam,
) -> Any:
    """按站点/详情链接重新刮削，仅返回结果不入库，供对比后更新"""
    service = MetadataService(session)
    db_metadata = service.get_by_id(id)
    if not db_metadata:
        raise HTTPException(status_code=404, detail=f"Metadata with id {id} not found")
    json_data = await asyncio.to_thread(
        service.scrape_from_source,
        db_metadata.number,
        params.site,
        params.detailurl,
        get_active_proxy(session),
    )
    if not json_data:
        raise HTTPException(status_code=404, detail="未找到元数据")
    return schemas.MetadataBase(**json_data)


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
