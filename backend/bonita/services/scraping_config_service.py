from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from bonita import schemas
from bonita.db.models.scraping import ScrapingConfig


class ScrapingConfigService:
    """刮削配置 CRUD。"""

    def __init__(self, session: Session):
        self.session = session

    def list_configs(self, skip: int = 0, limit: int = 100) -> Tuple[List[ScrapingConfig], int]:
        configs = self.session.query(ScrapingConfig).offset(skip).limit(limit).all()
        count = self.session.query(ScrapingConfig).count()
        return configs, count

    def get_by_id(self, config_id: int) -> Optional[ScrapingConfig]:
        return self.session.get(ScrapingConfig, config_id)

    def create_config(self, config_in: schemas.ScrapingConfigCreate) -> ScrapingConfig:
        config = ScrapingConfig(**config_in.model_dump())
        config.create(self.session)
        return config

    def update_config(self, config_id: int, update_dict: dict) -> Optional[ScrapingConfig]:
        config = self.get_by_id(config_id)
        if not config:
            return None
        config.update(self.session, update_dict)
        self.session.commit()
        self.session.refresh(config)
        return config

    def delete_config(self, config_id: int) -> Optional[ScrapingConfig]:
        config = self.get_by_id(config_id)
        if not config:
            return None
        self.session.delete(config)
        self.session.commit()
        return config
