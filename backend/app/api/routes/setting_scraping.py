
from typing import Any
from fastapi import APIRouter

from app import schemas
from app.api.deps import CurrentUser, SessionDep
from app.db.models.setting import ScrapingSetting


router = APIRouter()


@router.get("/all", response_model=schemas.ScrapingSettingsPublic)
def get_all_settings(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有配置.
    """
    settings = session.query(ScrapingSetting).offset(skip).limit(limit).all()
    count = session.query(ScrapingSetting).count()

    setting_list = [schemas.ScrapingSettingPublic.model_validate(setting) for setting in settings]
    return schemas.TransferTasksPublic(data=setting_list, count=count)


@router.post("/", response_model=schemas.ScrapingSettingPublic)
def create_setting(
    *, session: SessionDep, current_user: CurrentUser, setting_in: schemas.ScrapingSettingCreate
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
