from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas
from bonita.api.deps import CurrentUser, SessionDep
from bonita.services.scraping_config_service import ScrapingConfigService


router = APIRouter()


@router.get("/all", response_model=schemas.ScrapingConfigsPublic)
def get_all_configs(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有配置.
    """
    configs, count = ScrapingConfigService(session).list_configs(skip=skip, limit=limit)
    config_list = [schemas.ScrapingConfigPublic.model_validate(config) for config in configs]
    return schemas.ScrapingConfigsPublic(data=config_list, count=count)


@router.post("/", response_model=schemas.ScrapingConfigPublic)
def create_config(
    session: SessionDep, current_user: CurrentUser, config_in: schemas.ScrapingConfigCreate
) -> Any:
    """
    创建新配置
    """
    return ScrapingConfigService(session).create_config(config_in)


@router.put("/{id}", response_model=schemas.ScrapingConfigPublic)
def update_config(
    session: SessionDep,
    id: int,
    config_in: schemas.ScrapingConfigPublic,
) -> Any:
    """
    更新配置
    """
    config = ScrapingConfigService(session).update_config(
        id, config_in.model_dump(exclude_unset=True)
    )
    if not config:
        raise HTTPException(status_code=404, detail="配置未找到")
    return config


@router.delete("/{id}", response_model=schemas.Response)
def delete_config(
    session: SessionDep,
    id: int
) -> Any:
    """
    删除配置
    """
    config = ScrapingConfigService(session).delete_config(id)
    if not config:
        raise HTTPException(status_code=404, detail="配置未找到")
    return schemas.Response(success=True, message="配置删除成功")
