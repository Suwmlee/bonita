from typing import Any
from fastapi import APIRouter, HTTPException
import traceback

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.setting_service import SettingService

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
        success, message = SettingService(session).save_emby_settings(
            host=settings_in.emby_host,
            apikey=settings_in.emby_apikey,
            user=settings_in.emby_user,
            enabled=settings_in.enabled
        )
        return schemas.Response(success=success, message=message)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emby/test", response_model=schemas.Response)
def test_emby_connection(
    *,
    session: SessionDep,
    test_data: schemas.EmbySettings
) -> Any:
    """
    测试Emby连接和API Key是否有效.
    """
    success, message = SettingService(session).test_emby_connection(
        host=test_data.emby_host,
        apikey=test_data.emby_apikey,
        user=test_data.emby_user,
    )
    return schemas.Response(success=success, message=message)


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
    session: SessionDep,
    test_data: schemas.TransmissionSettings
) -> Any:
    """
    测试Transmission连接是否有效.
    """
    success, message = SettingService(session).test_transmission_connection(
        host=test_data.transmission_host,
        username=test_data.transmission_username,
        password=test_data.transmission_password,
        source_path=test_data.transmission_source_path or "",
        dest_path=test_data.transmission_dest_path or "",
    )
    return schemas.Response(success=success, message=message)


@router.get("/qbittorrent", response_model=schemas.QBittorrentSettings)
def get_qbittorrent_settings(session: SessionDep) -> Any:
    """
    获取qBittorrent下载器设置.
    """
    try:
        return SettingService(session).get_qbittorrent_settings()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qbittorrent", response_model=schemas.Response)
def update_qbittorrent_settings(
    *,
    session: SessionDep,
    settings_in: schemas.QBittorrentSettings,
) -> Any:
    """
    更新qBittorrent下载器设置.
    """
    try:
        SettingService(session).update_qbittorrent_settings(
            host=settings_in.qbittorrent_host,
            username=settings_in.qbittorrent_username,
            password=settings_in.qbittorrent_password,
            source_path=settings_in.qbittorrent_source_path or "",
            dest_path=settings_in.qbittorrent_dest_path or "",
            enabled=settings_in.enabled,
        )
        return schemas.Response(success=True, message="qBittorrent设置已更新")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qbittorrent/test", response_model=schemas.Response)
def test_qbittorrent_connection(
    *,
    session: SessionDep,
    test_data: schemas.QBittorrentSettings,
) -> Any:
    """
    测试qBittorrent连接是否有效.
    """
    success, message = SettingService(session).test_qbittorrent_connection(
        host=test_data.qbittorrent_host,
        username=test_data.qbittorrent_username,
        password=test_data.qbittorrent_password,
        source_path=test_data.qbittorrent_source_path or "",
        dest_path=test_data.qbittorrent_dest_path or "",
    )
    return schemas.Response(success=success, message=message)
