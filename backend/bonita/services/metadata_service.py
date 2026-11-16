import logging
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from bonita.db.models.actor import MetadataActor
from bonita.db.models.metadata import Metadata
from bonita.modules.scraping.scraping import scraping
from bonita.utils.assets import cover_folder_for_number
from bonita.utils.downloader import process_cached_file
from bonita.utils.http import get_active_proxy
from bonita.utils.numbers import normalize_number

logger = logging.getLogger(__name__)


class MetadataService:
    """元数据业务逻辑"""

    def __init__(self, session: Session):
        self.session = session

    def get_crop_by_numbers(self, numbers: List[Optional[str]]) -> dict:
        """按番号（大写）返回最新一条元数据的 crop。没有本地元数据的番号不会出现在结果中。"""
        result = {}
        keys = [normalize_number(n) for n in numbers if n]
        keys = [k for k in keys if k]
        if not keys:
            return result
        rows = (
            self.session.query(Metadata)
            .filter(func.upper(Metadata.number).in_(keys))
            .order_by(Metadata.id.asc())
            .all()
        )
        for row in rows:
            key = normalize_number(row.number)
            if key:
                result[key] = row.crop
        return result

    def resolve_crop(self, number: Optional[str], crop_map: Optional[dict] = None) -> bool:
        """没有本地 metadata 时默认不裁切；有则用 metadata.crop。"""
        key = normalize_number(number)
        if not key:
            return False
        source = crop_map if crop_map is not None else self.get_crop_by_numbers([key])
        crop = source.get(key)
        if crop is None:
            return False
        return bool(crop)

    def get_crop_by_number(self, number: Optional[str]) -> bool:
        return self.resolve_crop(number)

    def get_by_id(self, metadata_id: int) -> Optional[Metadata]:
        return self.session.get(Metadata, metadata_id)

    def get_by_number(self, number: str) -> Optional[Metadata]:
        key = normalize_number(number)
        if not key:
            return None
        return (
            self.session.query(Metadata)
            .filter(func.upper(Metadata.number) == key)
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
        from bonita.services.actor_service import ActorService

        actor_service = ActorService(self.session)
        if filter_text:
            actor_service.ensure_credits_backfilled()
        query = actor_service.filter_metadata_query(self.session.query(Metadata), filter_text)
        sort_column = getattr(Metadata, sort_by, Metadata.updatetime)
        query = query.order_by(sort_column.desc() if sort_desc else sort_column.asc())
        count = query.count()
        data = query.offset(skip).limit(limit).all()
        return data, count

    def _cache_cover_if_needed(self, payload: dict) -> None:
        folder = cover_folder_for_number(payload.get("number"))
        for key in ("cover", "cover_small"):
            url = payload.get(key)
            if not url or not str(url).startswith(("http://", "https://")):
                continue
            try:
                process_cached_file(self.session, str(url), folder)
            except Exception as e:
                logger.warning(f"封面下载失败（{key}），元数据仍将保存: {url} — {e}")

    def _sync_credits_for_metadata(self, metadata: Metadata) -> None:
        from bonita.services.actor_service import ActorService

        ActorService(self.session).replace_credits_for_metadata(
            metadata.id,
            metadata.actor,
            metadata.actor_photo,
            rewrite=True,
        )
        self.session.commit()
        self.session.refresh(metadata)

    def create_metadata(self, metadata_dict: dict) -> Metadata:
        actor_value = metadata_dict.get("actor")
        if not actor_value or (isinstance(actor_value, str) and actor_value.strip() == ""):
            metadata_dict["actor"] = "佚名"
        self._cache_cover_if_needed(metadata_dict)
        db_metadata = Metadata(**metadata_dict)
        db_metadata.create(self.session)
        self._sync_credits_for_metadata(db_metadata)
        from bonita.modules.media_service.record_link import attach_number_records
        attach_number_records(self.session, db_metadata.number or "", db_metadata.title or "")
        return db_metadata

    def update_metadata(self, metadata_id: int, update_dict: dict) -> Optional[Metadata]:
        db_metadata = self.get_by_id(metadata_id)
        if not db_metadata:
            return None
        update_dict.setdefault("number", db_metadata.number)
        self._cache_cover_if_needed(update_dict)
        db_metadata.update(self.session, update_dict)
        self.session.commit()
        self.session.refresh(db_metadata)
        self._sync_credits_for_metadata(db_metadata)
        from bonita.modules.media_service.record_link import attach_number_records
        attach_number_records(self.session, db_metadata.number or "", db_metadata.title or "")
        return db_metadata

    def delete_metadata(self, metadata_id: int) -> bool:
        db_metadata = self.get_by_id(metadata_id)
        if not db_metadata:
            return False
        self.session.query(MetadataActor).filter(
            MetadataActor.metadata_id == metadata_id
        ).delete(synchronize_session=False)
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
