from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas
from bonita.api.deps import CurrentUser, SessionDep
from bonita.services.transfer_config_service import TransferConfigService

router = APIRouter()


@router.get("/all", response_model=schemas.TransferConfigsPublic)
def get_all_task_configs(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有任务配置
    """
    task_configs, count = TransferConfigService(session).list_configs(skip=skip, limit=limit)
    config_list = [schemas.TransferConfigPublic.model_validate(config) for config in task_configs]
    return schemas.TransferConfigsPublic(data=config_list, count=count)


@router.post("/", response_model=schemas.TransferConfigPublic)
def create_task_config(
    session: SessionDep, current_user: CurrentUser, config_in: schemas.TransferConfigCreate
) -> Any:
    """
    创建新任务配置
    """
    return TransferConfigService(session).create_config(config_in)


@router.put("/{id}", response_model=schemas.TransferConfigPublic)
def update_task_config(
    session: SessionDep,
    id: int,
    config_in: schemas.TransferConfigPublic,
) -> Any:
    """
    更新任务配置
    """
    task_config = TransferConfigService(session).update_config(
        id, config_in.model_dump(exclude_unset=True)
    )
    if not task_config:
        raise HTTPException(status_code=404, detail="任务配置未找到")
    return task_config


@router.delete("/{id}", response_model=schemas.Response)
def delete_task_config(
    session: SessionDep,
    id: int
) -> Any:
    """
    删除任务配置
    """
    config = TransferConfigService(session).delete_config(id)
    if not config:
        raise HTTPException(status_code=404, detail="任务配置未找到")
    return schemas.Response(success=True, message="任务配置删除成功")
