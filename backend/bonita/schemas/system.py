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
