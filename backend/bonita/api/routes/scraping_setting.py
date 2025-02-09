
from typing import Any
from fastapi import APIRouter, HTTPException

from bonita import schemas
from bonita.api.deps import CurrentUser, SessionDep
from bonita.db.models.setting import ScrapingSetting


router = APIRouter()


@router.get("/all", response_model=schemas.ScrapingSettingsPublic)
def get_all_settings(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有配置.
    """
    settings = session.query(ScrapingSetting).offset(skip).limit(limit).all()
    count = session.query(ScrapingSetting).count()

    setting_list = [schemas.ScrapingSettingPublic.model_validate(setting) for setting in settings]
    return schemas.ScrapingSettingsPublic(data=setting_list, count=count)


@router.post("/", response_model=schemas.ScrapingSettingPublic)
def create_setting(
    session: SessionDep, current_user: CurrentUser, setting_in: schemas.ScrapingSettingCreate
) -> Any:
    """
    创建新配置
    """
    setting_info = setting_in.__dict__
    setting = ScrapingSetting(**setting_info)
    session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting


@router.put("/{id}", response_model=schemas.ScrapingSettingPublic)
def update_setting(
    session: SessionDep,
    id: int,
    setting_in: schemas.ScrapingSettingPublic,
) -> Any:
    """
    Update an setting.
    """
    setting = session.get(ScrapingSetting, id)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    update_dict = setting_in.model_dump(exclude_unset=True)
    setting.update(session, update_dict)
    session.commit()
    session.refresh(setting)
    return setting


@router.delete("/{id}", response_model=schemas.Response)
def delete_setting(
    session: SessionDep,
    id: int
) -> Any:
    """
    Delete an setting.
    """
    setting = session.get(ScrapingSetting, id)
    session.delete(setting)
    session.commit()
    return schemas.Response(success=True, message="ScrapingSetting deleted successfully")
