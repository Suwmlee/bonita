from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas
from bonita.api.deps import CurrentUser, SessionDep
from bonita.db.models.scraping import ScrapingConfig


router = APIRouter()


@router.get("/all", response_model=schemas.ScrapingConfigsPublic)
def get_all_configs(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有配置.
    """
    configs = session.query(ScrapingConfig).offset(skip).limit(limit).all()
    count = session.query(ScrapingConfig).count()

    config_list = [schemas.ScrapingConfigPublic.model_validate(config) for config in configs]
    return schemas.ScrapingConfigsPublic(data=config_list, count=count)


@router.post("/", response_model=schemas.ScrapingConfigPublic)
def create_config(
    session: SessionDep, current_user: CurrentUser, config_in: schemas.ScrapingConfigCreate
) -> Any:
    """
    创建新配置
    """
    config_info = config_in.__dict__
    config = ScrapingConfig(**config_info)
    config.create(session)
    return config


@router.put("/{id}", response_model=schemas.ScrapingConfigPublic)
def update_config(
    session: SessionDep,
    id: int,
    config_in: schemas.ScrapingConfigPublic,
) -> Any:
    """
    更新配置
    """
    config = session.get(ScrapingConfig, id)
    if not config:
        raise HTTPException(status_code=404, detail="配置未找到")
    update_dict = config_in.model_dump(exclude_unset=True)
    config.update(session, update_dict)
    session.commit()
    session.refresh(config)
    return config


@router.delete("/{id}", response_model=schemas.Response)
def delete_config(
    session: SessionDep,
    id: int
) -> Any:
    """
    删除配置
    """
    config = session.get(ScrapingConfig, id)
    session.delete(config)
    session.commit()
    return schemas.Response(success=True, message="配置删除成功") 