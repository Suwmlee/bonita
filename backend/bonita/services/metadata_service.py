import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from bonita.db.models.metadata import Metadata
from bonita.modules.scraping.scraping import scraping
from bonita.services.resource_service import cover_folder_for_number
from bonita.utils.actor_names import UNKNOWN_ACTOR, parse_actor_photos, split_actor_names
from bonita.utils.downloader import process_cached_file
from bonita.utils.http import get_active_proxy

logger = logging.getLogger(__name__)

_ACTOR_COVERS = 4


def _photo_for(photos: dict, name: str, only_actor: bool) -> Optional[str]:
    target = name.casefold()
    for key, url in photos.items():
        if key.casefold() == target:
            return url
    if only_actor and len(photos) == 1:
        return next(iter(photos.values()))
    return None


class _Reverse:
    """让字符串按降序参与升序排序，同时保持佚名排在最后。"""

    def __init__(self, value: str):
        self.value = value

    def __lt__(self, other: "_Reverse") -> bool:
        return self.value > other.value


def _like_contains(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


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

    def list_actors(
        self,
        skip: int = 0,
        limit: int = 24,
        filter_text: Optional[str] = None,
        sort: str = "count",
    ) -> Tuple[List[dict], int]:
        """按 Actor 表聚合作品数；同人别名合并。佚名始终排在最后。"""
        from bonita.services.actor_service import ActorService

        if sort == "count":
            sort = "count_desc"
        elif sort == "name":
            sort = "name_asc"
        elif sort not in ("count_desc", "count_asc", "name_asc", "name_desc"):
            sort = "count_desc"

        actor_service = ActorService(self.session)
        name_index = actor_service.load_name_index()

        query = self.session.query(
            Metadata.id,
            Metadata.actor,
            Metadata.actor_photo,
            Metadata.cover,
            Metadata.crop,
            Metadata.updatetime,
        )
        query = self._filter_query(query, filter_text)
        query = query.order_by(Metadata.updatetime.desc(), Metadata.id.desc())
        rows = query.all()

        buckets: dict = {}
        for row in rows:
            names = split_actor_names(row.actor)
            photos = parse_actor_photos(row.actor_photo)
            cover = (row.cover or "").strip()
            crop = True if row.crop is None else bool(row.crop)
            only_actor = len(names) == 1
            for name in names:
                actor = name_index.get(name.casefold())
                if actor is None:
                    continue
                key = ("id", actor.id)
                bucket = buckets.get(key)
                if bucket is None:
                    bucket = {
                        "id": actor.id,
                        "name": actor.name,
                        "photo": (actor.photo or "").strip() or None,
                        "count": 0,
                        "covers": [],
                        "cover_paths": set(),
                        "seen": set(),
                        "unknown": actor.name == UNKNOWN_ACTOR,
                    }
                    buckets[key] = bucket
                if row.id in bucket["seen"]:
                    continue
                bucket["seen"].add(row.id)
                bucket["count"] += 1
                if not bucket["photo"]:
                    bucket["photo"] = _photo_for(photos, name, only_actor)
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
        page = [
            {
                "id": item["id"],
                "name": item["name"],
                "photo": item["photo"],
                "count": item["count"],
                "covers": item["covers"],
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
    ) -> Tuple[List[Metadata], int]:
        """某一位演员的作品。优先按 Actor 别名集合匹配。"""
        from bonita.services.actor_service import ActorService

        name = (actor_name or "").strip()
        if not name:
            return [], 0

        actor_service = ActorService(self.session)
        actor = actor_service.find_by_name(name)
        if actor:
            name_keys = actor_service.alias_names_of(actor)
            alias_texts = {actor.name}
            alias_texts.update(a.name for a in (actor.aliases or []))
        else:
            name_keys = {name.casefold()}
            alias_texts = {name}

        query = self._filter_query(self.session.query(Metadata), filter_text)
        if UNKNOWN_ACTOR.casefold() in name_keys and len(name_keys) == 1:
            query = query.filter(or_(
                Metadata.actor.ilike(_like_contains(UNKNOWN_ACTOR), escape="\\"),
                Metadata.actor.is_(None),
                func.trim(Metadata.actor) == "",
            ))
        else:
            likes = [
                Metadata.actor.ilike(_like_contains(text), escape="\\")
                for text in alias_texts
            ]
            query = query.filter(or_(*likes))
        query = query.order_by(Metadata.updatetime.desc(), Metadata.id.desc())
        matched = [
            row for row in query.all()
            if any(part.casefold() in name_keys for part in split_actor_names(row.actor))
        ]
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

    def _sync_actors_from_payload(self, payload: dict) -> None:
        from bonita.services.actor_service import ActorService

        ActorService(self.session).ensure_from_metadata_fields(
            payload.get("actor"),
            payload.get("actor_photo"),
        )
        self.session.commit()

    def create_metadata(self, metadata_dict: dict) -> Metadata:
        actor_value = metadata_dict.get("actor")
        if not actor_value or (isinstance(actor_value, str) and actor_value.strip() == ""):
            metadata_dict["actor"] = "佚名"
        self._cache_cover_if_needed(metadata_dict)
        db_metadata = Metadata(**metadata_dict)
        db_metadata.create(self.session)
        self._sync_actors_from_payload(metadata_dict)
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
        self._sync_actors_from_payload({
            "actor": update_dict.get("actor", db_metadata.actor),
            "actor_photo": update_dict.get("actor_photo", db_metadata.actor_photo),
        })
        from bonita.modules.media_service.record_link import attach_number_records
        attach_number_records(self.session, db_metadata.number or "", db_metadata.title or "")
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
