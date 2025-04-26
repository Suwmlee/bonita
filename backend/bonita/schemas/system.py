from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class SystemSettingBase(BaseModel):
    """
    Shared properties
    """
    key: str
    value: Optional[str] = None
    description: Optional[str] = None


class SystemSettingCreate(SystemSettingBase):
    """
    Properties to receive on item creation
    """
    pass


class SystemSettingUpdate(BaseModel):
    """
    Properties to receive on item update
    """
    value: Optional[str] = None
    description: Optional[str] = None


class SystemSettingPublic(SystemSettingBase):
    """
    Properties to return to client
    """
    id: int
    updatetime: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProxySettings(BaseModel):
    """
    Proxy settings schema
    """
    http: Optional[str] = None
    https: Optional[str] = None
    enabled: Optional[bool] = False


class EmbySettings(BaseModel):
    """
    Emby settings schema
    """
    emby_host: str
    emby_apikey: str
    emby_user: str
    enabled: Optional[bool] = False


class JellyfinSettings(BaseModel):
    """
    Jellyfin settings schema
    """
    jellyfin_host: str
    jellyfin_apikey: str
    enabled: Optional[bool] = False


class TransmissionSettings(BaseModel):
    """
    Transmission downloader settings schema
    """
    transmission_host: str
    transmission_username: str
    transmission_password: str
    transmission_source_path: Optional[str] = ""
    transmission_dest_path: Optional[str] = ""
    enabled: Optional[bool] = False
