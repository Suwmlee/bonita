import logging
from typing import Optional

from bonita.modules.media_service.client import (
    SOURCE_EMBY,
    SOURCE_JELLYFIN,
    MediaServerClient,
    source_label,
)
from bonita.modules.media_service.emby import EmbyClient
from bonita.modules.media_service.jellyfin import JellyfinClient

logger = logging.getLogger(__name__)

_CLIENTS = {
    SOURCE_EMBY: EmbyClient,
    SOURCE_JELLYFIN: JellyfinClient,
}


def get_media_client(source: str = SOURCE_EMBY) -> Optional[MediaServerClient]:
    """返回已初始化的媒体服务器客户端。未启用或未初始化时返回 None。"""
    cls = _CLIENTS.get(source)
    if not cls:
        return None
    client = cls()
    return client if client.is_initialized else None


def require_media_client(source: str = SOURCE_EMBY) -> MediaServerClient:
    client = ensure_media_client(source)
    if not client:
        if source == SOURCE_EMBY:
            raise RuntimeError("Emby服务未初始化")
        raise RuntimeError(f"{source_label(source)}服务未初始化")
    return client


def ensure_media_client(source: str = SOURCE_EMBY) -> Optional[MediaServerClient]:
    client = get_media_client(source)
    if client:
        return client
    init_media_servers()
    return get_media_client(source)


def init_media_servers() -> None:
    """按设置初始化已启用的媒体服务器客户端。"""
    from bonita.db import SessionFactory
    from bonita.services.setting_service import SettingService

    with SessionFactory() as session:
        settings = SettingService(session).get_emby_settings()
        if not settings.get("enabled"):
            logger.info("Emby is not enabled")
            return
        host = settings.get("emby_host")
        apikey = settings.get("emby_apikey")
        user = settings.get("emby_user")
        if not host or not apikey or not user:
            logger.info("Emby host or API key or user not configured")
            return
        logger.info("initial EmbyClient")
        EmbyClient().initialize(host, apikey, user)
