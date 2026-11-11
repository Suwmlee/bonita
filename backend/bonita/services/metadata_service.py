import logging
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from bonita.db.models.actor import Actor, MetadataActor
from bonita.db.models.metadata import Metadata
from bonita.modules.scraping.scraping import scraping
from bonita.services.resource_service import cover_folder_for_number
from bonita.utils.actor_names import UNKNOWN_ACTOR
from bonita.utils.downloader import process_cached_file
from bonita.utils.http import get_active_proxy

logger = logging.getLogger(__name__)

_ACTOR_COVERS = 4


class _Reverse:
    """让字符串按降序参与升序排序，同时保持佚名排在最后。"""

    def __init__(self, value: str):
        self.value = value

    def __lt__(self, other: "_Reverse") -> bool:
        return self.value > other.value


class MetadataService:
    """元数据业务逻辑"""

    def __init__(self, session: Session):
        self.session = session

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

    def _filter_query(self, query, filter_text: Optional[str]):
        if not filter_text:
            return query
        like = f"%{filter_text}%"
        return query.filter(
            Metadata.number.ilike(like) | Metadata.actor.ilike(like)
        )

    def list_metadata(
        self,
        skip: int = 0,
        limit: int = 100,
        filter_text: Optional[str] = None,
        sort_by: str = "updatetime",
        sort_desc: bool = True,
    ) -> Tuple[List[Metadata], int]:
        query = self._filter_query(self.session.query(Metadata), filter_text)
        sort_column = getattr(Metadata, sort_by, Metadata.updatetime)
        query = query.order_by(sort_column.desc() if sort_desc else sort_column.asc())
        count = query.count()
        data = query.offset(skip).limit(limit).all()
        return data, count

    def _ensure_credits_backfilled(self) -> None:
        """旧库升级后若还没有出演行，自动从 Metadata.actor 回填一次。"""
        if self.session.query(MetadataActor.id).limit(1).first():
            return
        if not self.session.query(Metadata.id).limit(1).first():
            return
        from bonita.services.actor_service import ActorService

        logger.info("检测到无出演关联，开始从 Metadata.actor 回填 metadata_actor")
        ActorService(self.session).sync_from_metadata()

    def list_actors(
        self,
        skip: int = 0,
        limit: int = 24,
        filter_text: Optional[str] = None,
        sort: str = "count",
    ) -> Tuple[List[dict], int]:
        """按 metadata_actor.actor_id 聚合作品数。佚名始终排在最后。"""
        if sort == "count":
            sort = "count_desc"
        elif sort == "name":
            sort = "name_asc"
        elif sort not in ("count_desc", "count_asc", "name_asc", "name_desc"):
            sort = "count_desc"

        self._ensure_credits_backfilled()

        meta_query = self._filter_query(self.session.query(Metadata.id), filter_text)
        meta_ids = [row[0] for row in meta_query.all()]
        if not meta_ids:
            return [], 0

        credits = (
            self.session.query(MetadataActor)
            .join(Metadata, Metadata.id == MetadataActor.metadata_id)
            .options(
                joinedload(MetadataActor.actor).joinedload(Actor.aliases),
                joinedload(MetadataActor.metadata_row),
            )
            .filter(MetadataActor.metadata_id.in_(meta_ids))
            .order_by(Metadata.updatetime.desc(), Metadata.id.desc())
            .all()
        )

        buckets: dict = {}
        for credit in credits:
            actor = credit.actor
            meta = credit.metadata_row
            if not actor or not meta:
                continue
            bucket = buckets.get(actor.id)
            if bucket is None:
                primary_key = (actor.name or "").casefold()
                alias_names = []
                seen_alias = set()
                for alias in actor.aliases or []:
                    text = (alias.name or "").strip()
                    if not text:
                        continue
                    key = text.casefold()
                    if key == primary_key or key in seen_alias:
                        continue
                    seen_alias.add(key)
                    alias_names.append(text)
                bucket = {
                    "id": actor.id,
                    "name": actor.name,
                    "photo": (actor.photo or "").strip() or None,
                    "count": 0,
                    "covers": [],
                    "cover_paths": set(),
                    "seen": set(),
                    "unknown": actor.name == UNKNOWN_ACTOR,
                    "latest": None,
                    "aliases": alias_names,
                }
                buckets[actor.id] = bucket
            if meta.id in bucket["seen"]:
                continue
            bucket["seen"].add(meta.id)
            bucket["count"] += 1
            stamp = (meta.updatetime, meta.id)
            if bucket["latest"] is None or stamp > bucket["latest"]:
                bucket["latest"] = stamp
            cover = (meta.cover or "").strip()
            crop = True if meta.crop is None else bool(meta.crop)
            if cover and cover not in bucket["cover_paths"] and len(bucket["covers"]) < _ACTOR_COVERS:
                bucket["cover_paths"].add(cover)
                bucket["covers"].append({"path": cover, "crop": crop})

        def sort_key(item: dict):
            unknown = item["unknown"]
            name = item["name"].casefold()
            if sort in ("name", "name_asc"):
                return (unknown, name)
            if sort == "name_desc":
                return (unknown, _Reverse(name))
            if sort == "count_asc":
                return (unknown, item["count"], name)
            return (unknown, -item["count"], name)

        ordered = sorted(buckets.values(), key=sort_key)
        name_groups: dict = {}
        for item in ordered:
            key = (item["name"] or "").casefold()
            name_groups[key] = name_groups.get(key, 0) + 1
        page = [
            {
                "id": item["id"],
                "name": item["name"],
                "photo": item["photo"],
                "count": item["count"],
                "covers": item["covers"],
                "aliases": item["aliases"],
                "homonym_count": name_groups.get((item["name"] or "").casefold(), 1),
            }
            for item in ordered[skip:skip + limit]
        ]
        return page, len(ordered)

    def list_actor_works(
        self,
        actor_name: str,
        skip: int = 0,
        limit: int = 24,
        filter_text: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> Tuple[List[Metadata], int]:
        """某一位演员的作品：优先 actor_id，否则按名字解析。"""
        from bonita.services.actor_service import ActorService

        actor_service = ActorService(self.session)
        actor: Optional[Actor] = None
        if actor_id is not None:
            actor = actor_service.get_by_id(actor_id)
        if actor is None:
            name = (actor_name or "").strip()
            if not name:
                return [], 0
            actor = actor_service.find_by_name(name)
        if actor is None:
            return [], 0

        query = (
            self.session.query(Metadata)
            .join(MetadataActor, MetadataActor.metadata_id == Metadata.id)
            .filter(MetadataActor.actor_id == actor.id)
        )
        query = self._filter_query(query, filter_text)
        query = query.order_by(Metadata.updatetime.desc(), Metadata.id.desc())
        matched = query.all()
        return matched[skip:skip + limit], len(matched)

    def _cache_cover_if_needed(self, payload: dict) -> None:
        cover = payload.get("cover")
        if cover and str(cover).startswith(("http://", "https://")):
            try:
                process_cached_file(
                    self.session,
                    cover,
                    cover_folder_for_number(payload.get("number")),
                )
            except Exception as e:
                logger.warning(f"封面下载失败，元数据仍将保存: {cover} — {e}")

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
