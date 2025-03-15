import requests
from urllib.parse import urljoin
from typing import Any
from fastapi import APIRouter, HTTPException
import traceback

from bonita import schemas
from bonita.api.deps import SessionDep
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
    settings_in: schemas.ProxySettings
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


@router.get("/emby", response_model=schemas.EmbySettings)
def get_emby_settings(session: SessionDep) -> Any:
    """
    获取Emby设置.
    """
    try:
        emby_setting_db = session.query(SystemSetting).filter(
            SystemSetting.key.in_(["emby_host", "emby_apikey", "emby_user", "emby_enabled"])
        ).all()
        emby_dict = {setting.key: setting.value for setting in emby_setting_db}
        emby_settings = {
            "emby_host": emby_dict.get("emby_host", ""),
            "emby_apikey": emby_dict.get("emby_apikey", ""),
            "emby_user": emby_dict.get("emby_user", ""),
            "enabled": emby_dict.get("emby_enabled", "false").lower() == "true"
        }

        return emby_settings
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emby", response_model=schemas.Response)
def update_emby_settings(
    *,
    session: SessionDep,
    settings_in: schemas.EmbySettings
) -> Any:
    """
    更新Emby设置.
    """
    try:
        # 保存Emby设置
        SystemSetting.set_setting(
            session,
            "emby_enabled",
            str(settings_in.enabled).lower(),
            "是否启用Emby"
        )

        SystemSetting.set_setting(
            session,
            "emby_host",
            settings_in.emby_host,
            "Emby服务器地址"
        )

        SystemSetting.set_setting(
            session,
            "emby_apikey",
            settings_in.emby_apikey,
            "Emby API密钥"
        )

        SystemSetting.set_setting(
            session,
            "emby_user",
            settings_in.emby_user,
            "Emby用户名"
        )
        return schemas.Response(
            success=True,
            message="Emby设置已更新"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emby/test", response_model=schemas.Response)
def test_emby_connection(
    *,
    test_data: schemas.EmbySettings
) -> Any:
    """
    测试Emby连接和API Key是否有效.
    """

    try:
        # 构建Emby API URL
        base_url = test_data.emby_host.rstrip('/')
        api_url = urljoin(f"{base_url}/", "emby/System/Info")

        # 添加API Key到请求头
        headers = {
            "X-Emby-Token": test_data.emby_apikey
        }

        # 发送请求测试连接
        response = requests.get(api_url, headers=headers, timeout=10)

        # 检查响应
        if response.status_code == 200:
            return schemas.Response(
                success=True,
                message="Emby连接成功，API Key有效"
            )
        else:
            return schemas.Response(
                success=False,
                message=f"Emby连接失败，状态码: {response.status_code}"
            )
    except requests.RequestException as e:
        return schemas.Response(
            success=False,
            message=f"Emby连接失败: {str(e)}"
        )
    except Exception as e:
        traceback.print_exc()
        return schemas.Response(
            success=False,
            message=f"测试Emby连接时出错: {str(e)}"
        )


@router.get("/jellyfin", response_model=schemas.JellyfinSettings)
def get_jellyfin_settings(session: SessionDep) -> Any:
    """
    获取Jellyfin设置.
    """
    try:
        jellyfin_setting_db = session.query(SystemSetting).filter(
            SystemSetting.key.in_(["jellyfin_host", "jellyfin_apikey", "jellyfin_enabled"])
        ).all()
        jellyfin_dict = {setting.key: setting.value for setting in jellyfin_setting_db}
        jellyfin_settings = {
            "jellyfin_host": jellyfin_dict.get("jellyfin_host", ""),
            "jellyfin_apikey": jellyfin_dict.get("jellyfin_apikey", ""),
            "enabled": jellyfin_dict.get("jellyfin_enabled", "false").lower() == "true"
        }

        return jellyfin_settings
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jellyfin", response_model=schemas.Response)
def update_jellyfin_settings(
    *,
    session: SessionDep,
    settings_in: schemas.JellyfinSettings
) -> Any:
    """
    更新Jellyfin设置.
    """
    try:
        # 保存Jellyfin设置
        SystemSetting.set_setting(
            session,
            "jellyfin_enabled",
            str(settings_in.enabled).lower(),
            "是否启用Jellyfin"
        )

        SystemSetting.set_setting(
            session,
            "jellyfin_host",
            settings_in.jellyfin_host,
            "Jellyfin服务器地址"
        )

        SystemSetting.set_setting(
            session,
            "jellyfin_apikey",
            settings_in.jellyfin_apikey,
            "Jellyfin API密钥"
        )

        return schemas.Response(
            success=True,
            message="Jellyfin设置已更新"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jellyfin/test", response_model=schemas.Response)
def test_jellyfin_connection(
    *,
    test_data: schemas.JellyfinSettings
) -> Any:
    """
    测试Jellyfin连接和API Key是否有效.
    """

    try:
        # 构建Jellyfin API URL
        base_url = test_data.jellyfin_host.rstrip('/')
        api_url = urljoin(f"{base_url}/", "System/Info")

        # 添加API Key到请求头
        headers = {
            "X-Emby-Token": test_data.jellyfin_apikey
        }

        # 发送请求测试连接
        response = requests.get(api_url, headers=headers, timeout=10)

        # 检查响应
        if response.status_code == 200:
            return schemas.Response(
                success=True,
                message="Jellyfin连接成功，API Key有效"
            )
        else:
            return schemas.Response(
                success=False,
                message=f"Jellyfin连接失败，状态码: {response.status_code}"
            )
    except requests.RequestException as e:
        return schemas.Response(
            success=False,
            message=f"Jellyfin连接失败: {str(e)}"
        )
    except Exception as e:
        traceback.print_exc()
        return schemas.Response(
            success=False,
            message=f"测试Jellyfin连接时出错: {str(e)}"
        )
