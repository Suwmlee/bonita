from typing import List, Optional
from pydantic import BaseModel


class ScrapingSettingBase(BaseModel):
    """
    Shared properties
    """
    name: str
    description: str
    save_metadata: bool = False


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
    scraping_sites: Optional[str] = None
    location_rule: Optional[str] = None
    naming_rule: Optional[str] = None
    max_title_len: Optional[int] = 50
    watermark_enabled: Optional[bool] = True
