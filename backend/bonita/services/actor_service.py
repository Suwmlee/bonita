import logging
from typing import Dict, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from bonita.db.models.actor import Actor, ActorAlias
from bonita.db.models.metadata import Metadata
from bonita.utils.actor_names import UNKNOWN_ACTOR, parse_actor_photos, split_actor_names

logger = logging.getLogger(__name__)


def _norm_key(name: str) -> str:
    return name.casefold()


class ActorService:
    """演员词典：从元数据回填、按别名解析。头像只存 URL，展示时按需下载。"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, actor_id: int) -> Optional[Actor]:
        return (
            self.session.query(Actor)
            .options(joinedload(Actor.aliases))
            .filter(Actor.id == actor_id)
            .first()
        )

    def find_by_name(self, name: str) -> Optional[Actor]:
        """按主名或别名匹配（大小写不敏感）。"""
        text = (name or "").strip()
        if not text:
            return None
        alias = (
            self.session.query(ActorAlias)
            .options(joinedload(ActorAlias.actor).joinedload(Actor.aliases))
            .filter(func.lower(ActorAlias.name) == text.lower())
            .first()
        )
        return alias.actor if alias else None

    def load_name_index(self) -> Dict[str, Actor]:
        """别名/主名 casefold → Actor。"""
        index: Dict[str, Actor] = {}
        actors = (
            self.session.query(Actor)
            .options(joinedload(Actor.aliases))
            .all()
        )
        for actor in actors:
            index[_norm_key(actor.name)] = actor
            for alias in actor.aliases:
                index[_norm_key(alias.name)] = actor
        return index

    def alias_names_of(self, actor: Actor) -> Set[str]:
        names = {_norm_key(actor.name)}
        for alias in actor.aliases or []:
            names.add(_norm_key(alias.name))
        return names

    def ensure_alias(self, actor: Actor, name: str) -> bool:
        """追加别名；精确同名或同人大小写变体已存在则跳过。"""
        text = (name or "").strip()
        if not text:
            return False
        existing = (
            self.session.query(ActorAlias)
            .filter(ActorAlias.name == text)
            .first()
        )
        if existing:
            return False
        same_fold = (
            self.session.query(ActorAlias)
            .filter(
                ActorAlias.actor_id == actor.id,
                func.lower(ActorAlias.name) == text.lower(),
            )
            .first()
        )
        if same_fold:
            return False
        self.session.add(ActorAlias(actor_id=actor.id, name=text))
        self.session.flush()
        return True

    def ensure_actor(
        self,
        name: str,
        photo: Optional[str] = None,
        name_index: Optional[Dict[str, Actor]] = None,
    ) -> Actor:
        """确保名字对应的演员存在；已有则补空头像 URL，不下载。"""
        text = (name or "").strip() or UNKNOWN_ACTOR
        photo_url = (photo or "").strip()
        index = name_index if name_index is not None else self.load_name_index()
        key = _norm_key(text)
        actor = index.get(key)
        if actor:
            if photo_url and not (actor.photo or "").strip():
                actor.photo = photo_url
            self.ensure_alias(actor, text)
            index[key] = actor
            return actor

        actor = Actor(name=text, photo=photo_url or "")
        self.session.add(actor)
        self.session.flush()
        self.session.add(ActorAlias(actor_id=actor.id, name=text))
        self.session.flush()
        index[key] = actor
        return actor

    def ensure_from_metadata_fields(
        self,
        actor_field: Optional[str],
        actor_photo_field: Optional[str] = None,
        name_index: Optional[Dict[str, Actor]] = None,
    ) -> List[Actor]:
        names = split_actor_names(actor_field)
        photos = parse_actor_photos(actor_photo_field)
        only_one = len(names) == 1
        index = name_index if name_index is not None else self.load_name_index()
        result = []
        for name in names:
            photo = None
            for photo_key, url in photos.items():
                if _norm_key(photo_key) == _norm_key(name):
                    photo = url
                    break
            if not photo and only_one and len(photos) == 1:
                photo = next(iter(photos.values()))
            result.append(self.ensure_actor(name, photo, name_index=index))
        return result

    def sync_from_metadata(self) -> dict:
        """扫描全部 Metadata.actor，写入 Actor / ActorAlias。

        同一名字（忽略大小写）只建一个人；头像只记 URL，展示时再下载。
        """
        before_count = self.session.query(Actor).count()
        rows = (
            self.session.query(
                Metadata.actor,
                Metadata.actor_photo,
                Metadata.updatetime,
                Metadata.id,
            )
            .order_by(Metadata.updatetime.desc(), Metadata.id.desc())
            .all()
        )
        name_index = self.load_name_index()
        seen_keys: Set[str] = set()

        for row in rows:
            names = split_actor_names(row.actor)
            photos = parse_actor_photos(row.actor_photo)
            only_one = len(names) == 1
            for name in names:
                key = _norm_key(name)
                photo = None
                for photo_key, url in photos.items():
                    if _norm_key(photo_key) == key:
                        photo = url
                        break
                if not photo and only_one and len(photos) == 1:
                    photo = next(iter(photos.values()))
                self.ensure_actor(name, photo, name_index=name_index)
                seen_keys.add(key)

        self.session.commit()
        total = self.session.query(Actor).count()
        alias_total = self.session.query(ActorAlias).count()
        created = max(0, total - before_count)
        logger.info(
            "演员回填完成: scanned=%s created=%s actors=%s aliases=%s",
            len(seen_keys),
            created,
            total,
            alias_total,
        )
        return {
            "scanned_names": len(seen_keys),
            "created": created,
            "actors": total,
            "aliases": alias_total,
        }
