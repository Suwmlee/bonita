from typing import List, Optional
from pydantic import BaseModel


class ScrapingSettingBase(BaseModel):
    """
    Shared properties
    """
    name: str
    description: str
    save_metadata: Optional[bool] = False
    scraping_sites: Optional[str] = None
    location_rule: Optional[str] = None
    naming_rule: Optional[str] = None
    max_title_len: Optional[int] = None
    morestoryline: Optional[bool] = True
    extrafanart_enabled: Optional[bool] = False
    extrafanart_folder: Optional[str] = 'extrafanart'
    watermark_enabled: Optional[bool] = True
    watermark_size: Optional[int] = 9
    watermark_location: Optional[int] = 2
    transalte_enabled: Optional[bool] = False
    transalte_to_sc: Optional[bool] = False
    transalte_values: Optional[str] = "title,outline"


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
    name: str
