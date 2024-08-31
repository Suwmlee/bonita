

from sqlalchemy import Column, Integer, String, Boolean

from app.db import Base


class ScrapingConfig(Base):
    """
    """
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default='movie')
    description = Column(String, default='')
    save_metadata = Column(Boolean, default=True)

    scraping_sites = Column(String, default="")
    location_rule = Column(String, default="actor+'/'+number+' '+title")
    naming_rule = Column(String, default="number+' '+title")
    max_title_len = Column(Integer, default=50)

    morestoryline = Column(Boolean, default=True)
    extrafanart_enabled = Column(Boolean, default=False)
    extrafanart_folder = Column(String, default='extrafanart')
    watermark_enabled = Column(Boolean, default=True)
    watermark_size = Column(Integer, default=9)
    watermark_location = Column(Integer, default=2)
    transalte_enabled = Column(Boolean, default=False)
    transalte_to_sc = Column(Boolean, default=False)
    transalte_values = Column(String, default="title,outline")
