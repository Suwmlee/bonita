from typing import List, Optional
from pydantic import BaseModel


class ScrapingSettingBase(BaseModel):
    """
    Shared properties
    """
    name: str
    description: str
    save_metadata: bool = False
    scraping_sites: Optional[str] = None
    location_rule: Optional[str] = None
    naming_rule: Optional[str] = None
    max_title_len: Optional[str] = None


class ScrapingSettingPublic(ScrapingSettingBase):
    """
    Properties to return via API, id is always required
    """
    id: int

    class Config:
        from_attributes = True


class ScrapingSettingsPublic(BaseModel):
    data: List[ScrapingSettingPublic]
    count: int


class ScrapingSettingCreate(ScrapingSettingBase):
    location_rule: str
    naming_rule: str
    watermark_enabled: bool = False
