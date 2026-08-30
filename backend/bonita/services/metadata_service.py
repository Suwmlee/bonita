import logging
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from bonita.db.models.metadata import Metadata
from bonita.modules.scraping.scraping import scraping
from bonita.utils.downloader import process_cached_file
from bonita.utils.http import get_active_proxy

logger = logging.getLogger(__name__)


class MetadataService:
    """元数据业务逻辑"""

    def __init__(self, session: Session):
        self.session = session

    def sync_crop_by_number(self, number: str, crop: bool) -> None:
        """将裁切标记同步到该番号对应的全部元数据。"""
        if not number:
            return
        self.session.query(Metadata).filter(
            func.upper(Metadata.number) == number.upper()
        ).update({Metadata.crop: crop}, synchronize_session="fetch")

    def get_crop_by_numbers(self, numbers: List[Optional[str]]) -> dict:
        """按番号（大写）返回最新一条元数据的 crop。没有本地元数据的番号不会出现在结果中。"""
        result = {}
        keys = [n.upper() for n in numbers if n]
        if not keys:
            return result
        rows = (
            self.session.query(Metadata)
            .filter(func.upper(Metadata.number).in_(keys))
            .order_by(Metadata.id.asc())
            .all()
        )
        for row in rows:
            if row.number:
                result[row.number.upper()] = row.crop
        return result

    def resolve_crop(self, number: Optional[str], crop_map: Optional[dict] = None) -> bool:
        """没有本地 metadata 时默认不裁切；有则用 metadata.crop。"""
        if not number:
            return False
        source = crop_map if crop_map is not None else self.get_crop_by_numbers([number])
        crop = source.get(number.upper())
        if crop is None:
            return False
        return bool(crop)

    def get_crop_by_number(self, number: Optional[str]) -> bool:
        return self.resolve_crop(number)

    def get_by_id(self, metadata_id: int) -> Optional[Metadata]:
        return self.session.get(Metadata, metadata_id)

    def get_by_number(self, number: str) -> Optional[Metadata]:
        if not number:
            return None
        return (
            self.session.query(Metadata)
            .filter(func.upper(Metadata.number) == number.upper())
            .first()
        )

    def list_metadata(
        self,
        skip: int = 0,
        limit: int = 100,
        filter_text: Optional[str] = None,
        sort_by: str = "updatetime",
        sort_desc: bool = True,
    ) -> Tuple[List[Metadata], int]:
        query = self.session.query(Metadata)
        if filter_text:
            query = query.filter(
                Metadata.number.ilike(f"%{filter_text}%") |
                Metadata.actor.ilike(f"%{filter_text}%")
            )
        sort_column = getattr(Metadata, sort_by, Metadata.updatetime)
        query = query.order_by(sort_column.desc() if sort_desc else sort_column.asc())
        count = query.count()
        data = query.offset(skip).limit(limit).all()
        return data, count

    def _cache_cover_if_needed(self, payload: dict) -> None:
        cover = payload.get("cover")
        if cover and str(cover).startswith(("http://", "https://")):
            process_cached_file(self.session, cover, payload.get("number"))

    def create_metadata(self, metadata_dict: dict) -> Metadata:
        actor_value = metadata_dict.get("actor")
        if not actor_value or (isinstance(actor_value, str) and actor_value.strip() == ""):
            metadata_dict["actor"] = "佚名"
        self._cache_cover_if_needed(metadata_dict)
        db_metadata = Metadata(**metadata_dict)
        db_metadata.create(self.session)
        return db_metadata

    def update_metadata(self, metadata_id: int, update_dict: dict) -> Optional[Metadata]:
        db_metadata = self.get_by_id(metadata_id)
        if not db_metadata:
            return None
        self._cache_cover_if_needed(update_dict)
        db_metadata.update(self.session, update_dict)
        self.session.commit()
        self.session.refresh(db_metadata)
        return db_metadata

    def delete_metadata(self, metadata_id: int) -> bool:
        db_metadata = self.get_by_id(metadata_id)
        if not db_metadata:
            return False
        self.session.delete(db_metadata)
        self.session.commit()
        return True

    def scrape_from_source(
        self,
        number: str,
        site: Optional[str] = None,
        detailurl: Optional[str] = None,
        proxy: Optional[dict] = None,
    ) -> Optional[dict]:
        """按番号从指定站点刮削，不写入数据库。"""
        site = (site or "").strip()
        detailurl = (detailurl or "").strip()
        logger.info(
            f"  → 刮削刷新: {number} | site={site or '-'} | detailurl={detailurl or '-'}"
        )
        if proxy is None:
            proxy = get_active_proxy(self.session)
        json_data = scraping(
            number,
            sources=site or None,
            specifiedsource=site,
            specifiedurl=detailurl,
            proxy=proxy,
        )
        if not json_data:
            logger.warning(f"  ⊘ 刮削刷新失败: {number}")
            return None
        json_data.setdefault("number", number)
        json_data.setdefault("cover", "")
        logger.info(f"  ✓ 刮削刷新成功: {json_data.get('title', number)}")
        return json_data
