import requests
from urllib.parse import urljoin
from typing import Any
from fastapi import APIRouter, HTTPException
import traceback

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.setting_service import SettingService
from bonita.modules.media_service.emby import EmbyService
from bonita.modules.download_clients.transmission import TransmissionClient

router = APIRouter()


@router.get("/proxy", response_model=schemas.ProxySettings)
def get_proxy_settings(session: SessionDep) -> Any:
    """
    获取代理设置.
    """
    try:
        setting_service = SettingService(session)
        return setting_service.get_proxy_settings()
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
        setting_service = SettingService(session)
        setting_service.update_proxy_settings(
            enabled=settings_in.enabled,
            http=settings_in.http,
            https=settings_in.https
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
        setting_service = SettingService(session)
        return setting_service.get_emby_settings()
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
        setting_service = SettingService(session)

        # 如果启用了Emby，则立即初始化EmbyService以验证连接
        if settings_in.enabled:
            emby_service = EmbyService()
            init_success = emby_service.initialize(
                emby_host=settings_in.emby_host,
                emby_apikey=settings_in.emby_apikey,
                emby_user=settings_in.emby_user
            )
            if not init_success:
                return schemas.Response(
                    success=False,
                    message="Emby设置已保存但初始化失败，请检查设置是否正确"
                )

        # 更新设置
        setting_service.update_emby_settings(
            host=settings_in.emby_host,
            apikey=settings_in.emby_apikey,
            user=settings_in.emby_user,
            enabled=settings_in.enabled
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
        # 使用EmbyService进行连接测试
        emby_service = EmbyService()
        init_success = emby_service.initialize(
            emby_host=test_data.emby_host,
            emby_apikey=test_data.emby_apikey,
            emby_user=test_data.emby_user
        )

        if init_success:
            return schemas.Response(
                success=True,
                message="Emby连接成功，API Key有效"
            )
        else:
            return schemas.Response(
                success=False,
                message="Emby连接失败，请检查服务器地址、API Key和用户名"
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
        setting_service = SettingService(session)
        return setting_service.get_jellyfin_settings()
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
        setting_service = SettingService(session)
        setting_service.update_jellyfin_settings(
            host=settings_in.jellyfin_host,
            apikey=settings_in.jellyfin_apikey,
            enabled=settings_in.enabled
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


@router.get("/transmission", response_model=schemas.TransmissionSettings)
def get_transmission_settings(session: SessionDep) -> Any:
    """
    获取Transmission下载器设置.
    """
    try:
        setting_service = SettingService(session)
        return setting_service.get_transmission_settings()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transmission", response_model=schemas.Response)
def update_transmission_settings(
    *,
    session: SessionDep,
    settings_in: schemas.TransmissionSettings
) -> Any:
    """
    更新Transmission下载器设置.
    """
    try:
        setting_service = SettingService(session)
        setting_service.update_transmission_settings(
            host=settings_in.transmission_host,
            username=settings_in.transmission_username,
            password=settings_in.transmission_password,
            source_path=settings_in.transmission_source_path,
            dest_path=settings_in.transmission_dest_path,
            enabled=settings_in.enabled
        )

        return schemas.Response(
            success=True,
            message="Transmission设置已更新"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transmission/test", response_model=schemas.Response)
def test_transmission_connection(
    *,
    test_data: schemas.TransmissionSettings
) -> Any:
    """
    测试Transmission连接是否有效.
    """
    try:
        # 使用TransmissionClient进行连接测试
        transmission_client = TransmissionClient()
        init_success = transmission_client.initialize(
            url=test_data.transmission_host,
            username=test_data.transmission_username,
            password=test_data.transmission_password,
            source_path=test_data.transmission_source_path,
            dest_path=test_data.transmission_dest_path
        )

        if init_success:
            return schemas.Response(
                success=True,
                message="Transmission连接成功"
            )
        else:
            return schemas.Response(
                success=False,
                message="Transmission连接失败，请检查服务器地址、用户名和密码"
            )
    except Exception as e:
        traceback.print_exc()
        return schemas.Response(
            success=False,
            message=f"测试Transmission连接时出错: {str(e)}"
        )
