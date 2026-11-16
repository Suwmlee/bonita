import logging
from typing import Optional

from bonita.modules.media_service.client import (
    SOURCE_EMBY,
    SOURCE_PLEX,
    CollectionCapable,
    MediaServerClient,
    PlaylistCapable,
    source_label,
)
from bonita.modules.media_service.emby import EmbyClient
from bonita.modules.media_service.plex import PlexClient

logger = logging.getLogger(__name__)

_CLIENTS = {
    SOURCE_EMBY: EmbyClient,
    SOURCE_PLEX: PlexClient,
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
        if source == SOURCE_PLEX:
            raise RuntimeError("Plex服务未初始化")
        raise RuntimeError(f"{source_label(source)}服务未初始化")
    return client


def require_collection_client(source: str = SOURCE_EMBY) -> CollectionCapable:
    """合集同步用：需已初始化且实现 CollectionCapable（当前仅 Emby）。"""
    client = require_media_client(source)
    if not isinstance(client, CollectionCapable):
        raise RuntimeError(f"{source_label(source)}不支持合集同步")
    return client


def ensure_media_client(source: str = SOURCE_EMBY) -> Optional[MediaServerClient]:
    client = get_media_client(source)
    if client:
        return client
    init_media_servers()
    return get_media_client(source)


def get_plex_client() -> Optional[PlexClient]:
    client = ensure_media_client(SOURCE_PLEX)
    return client if isinstance(client, PlexClient) else None


def require_plex_client() -> PlexClient:
    client = get_plex_client()
    if not client:
        raise RuntimeError("Plex服务未初始化")
    if not isinstance(client, PlaylistCapable):
        raise RuntimeError("Plex不支持播放列表同步")
    return client


def ensure_plex_client() -> Optional[PlexClient]:
    return get_plex_client()


def init_media_servers() -> None:
    """按设置初始化已启用的媒体服务器客户端。"""
    from bonita.db import SessionFactory
    from bonita.services.setting_service import SettingService

    with SessionFactory() as session:
        settings = SettingService(session).get_emby_settings()
        if not settings.get("enabled"):
            logger.info("Emby is not enabled")
        else:
            host = settings.get("emby_host")
            apikey = settings.get("emby_apikey")
            user = settings.get("emby_user")
            if not host or not apikey or not user:
                logger.info("Emby host or API key or user not configured")
            else:
                logger.info("initial EmbyClient")
                EmbyClient().initialize(host, apikey, user)

        plex_settings = SettingService(session).get_plex_settings()
        if not plex_settings.get("enabled"):
            logger.info("Plex is not enabled")
            return
        plex_host = plex_settings.get("plex_host")
        plex_token = plex_settings.get("plex_token")
        if not plex_host or not plex_token:
            logger.info("Plex host or token not configured")
            return
        logger.info("initial PlexClient")
        PlexClient().initialize(plex_host, plex_token)
