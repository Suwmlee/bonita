import json
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
import traceback

from bonita import schemas
from bonita.api.deps import CurrentUser, SessionDep
from bonita.db.models.setting import SystemSetting

router = APIRouter()


@router.get("/proxy", response_model=schemas.ProxySettings)
def get_proxy_settings(session: SessionDep) -> Any:
    """
    获取代理设置.
    """
    try:
        proxy_setting_db = session.query(SystemSetting).filter(
            SystemSetting.key.in_(["proxy_enabled", "proxy_http", "proxy_https"])
        ).all()
        proxy_dict = {setting.key: setting.value for setting in proxy_setting_db}
        proxy_settings = {
            "enabled": proxy_dict.get("proxy_enabled", "false").lower() == "true",
            "http": proxy_dict.get("proxy_http", ""),
            "https": proxy_dict.get("proxy_https", "")
        }

        return proxy_settings
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proxy", response_model=schemas.Response)
def update_proxy_settings(
    *,
    session: SessionDep,
    settings_in: schemas.ProxySettings,
    current_user: CurrentUser
) -> Any:
    """
    更新代理设置.
    """
    try:
        # 保存代理设置
        SystemSetting.set_setting(
            session,
            "proxy_enabled",
            str(settings_in.enabled).lower(),
            "是否启用代理"
        )

        if settings_in.http:
            SystemSetting.set_setting(
                session,
                "proxy_http",
                settings_in.http,
                "HTTP代理地址"
            )

        if settings_in.https:
            SystemSetting.set_setting(
                session,
                "proxy_https",
                settings_in.https,
                "HTTPS代理地址"
            )

        return schemas.Response(
            success=True,
            message="代理设置已更新"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
