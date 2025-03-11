from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas
from bonita.api.deps import CurrentUser, SessionDep
from bonita.db.models.task import TransferConfig
from bonita.watcher.manager import watcher_manager

router = APIRouter()


@router.get("/all", response_model=schemas.TransferConfigsPublic)
def get_all_task_configs(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有任务配置
    """
    task_configs = session.query(TransferConfig).offset(skip).limit(limit).all()
    count = session.query(TransferConfig).count()

    config_list = [schemas.TransferConfigPublic.model_validate(config) for config in task_configs]
    return schemas.TransferConfigsPublic(data=config_list, count=count)


@router.post("/", response_model=schemas.TransferConfigPublic)
def create_task_config(
    session: SessionDep, current_user: CurrentUser, config_in: schemas.TransferConfigCreate
) -> Any:
    """
    创建新任务配置
    """
    config_info = config_in.__dict__
    task_config = TransferConfig(**config_info)
    task_config.create(session)

    if task_config.auto_watch:
        watcher_manager.add_directory(task_config.source_folder, task_config.id)
    else:
        watcher_manager.remove_directory(task_config.source_folder, task_config.id)
    return task_config


@router.put("/{id}", response_model=schemas.TransferConfigPublic)
def update_task_config(
    session: SessionDep,
    id: int,
    config_in: schemas.TransferConfigPublic,
) -> Any:
    """
    更新任务配置
    """
    task_config = session.get(TransferConfig, id)
    if not task_config:
        raise HTTPException(status_code=404, detail="任务配置未找到")
    update_dict = config_in.model_dump(exclude_unset=True)
    task_config.update(session, update_dict)
    session.commit()
    session.refresh(task_config)

    if task_config.auto_watch:
        watcher_manager.add_directory(task_config.source_folder, task_config.id)
    return task_config


@router.delete("/{id}", response_model=schemas.Response)
def delete_task_config(
    session: SessionDep,
    id: int
) -> Any:
    """
    删除任务配置
    """
    config = session.get(TransferConfig, id)
    if config.auto_watch:
        watcher_manager.remove_directory(config.source_folder, config.id)
    session.delete(config)
    session.commit()

    return schemas.Response(success=True, message="任务配置删除成功")
