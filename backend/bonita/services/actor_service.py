import json
import logging
from typing import Dict, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from bonita.db.models.actor import Actor, ActorAlias, MetadataActor
from bonita.db.models.metadata import Metadata
from bonita.utils.actor_names import UNKNOWN_ACTOR, parse_actor_photos, split_actor_names

logger = logging.getLogger(__name__)


def _norm_key(name: str) -> str:
    return name.casefold()


class ActorService:
    """演员词典与出演关联：别名认人，metadata_actor 用 id 挂片，写出用主名。"""

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

    def replace_credits_for_metadata(
        self,
        metadata_id: int,
        actor_field: Optional[str],
        actor_photo_field: Optional[str] = None,
        name_index: Optional[Dict[str, Actor]] = None,
        rewrite: bool = True,
    ) -> List[MetadataActor]:
        """按当前演员字段重写该片出演行；同人只留一行。"""
        names = split_actor_names(actor_field)
        actors = self.ensure_from_metadata_fields(
            actor_field, actor_photo_field, name_index=name_index
        )
        self.session.query(MetadataActor).filter(
            MetadataActor.metadata_id == metadata_id
        ).delete(synchronize_session=False)

        credits: List[MetadataActor] = []
        seen_ids: Set[int] = set()
        sort = 0
        for name, actor in zip(names, actors):
            if actor.id in seen_ids:
                continue
            seen_ids.add(actor.id)
            credit = MetadataActor(
                metadata_id=metadata_id,
                actor_id=actor.id,
                credit_name=name,
                sort=sort,
            )
            self.session.add(credit)
            credits.append(credit)
            sort += 1
        self.session.flush()
        if rewrite:
            self.rewrite_metadata_actor_fields(metadata_id)
        return credits

    def rewrite_metadata_actor_fields(self, metadata_id: int) -> None:
        """按出演顺序用主名回写 Metadata.actor / actor_photo 键。"""
        meta = self.session.get(Metadata, metadata_id)
        if not meta:
            return
        credits = (
            self.session.query(MetadataActor)
            .options(joinedload(MetadataActor.actor))
            .filter(MetadataActor.metadata_id == metadata_id)
            .order_by(MetadataActor.sort.asc(), MetadataActor.id.asc())
            .all()
        )
        if not credits:
            meta.actor = UNKNOWN_ACTOR
            return

        primary_names = []
        for credit in credits:
            name = (credit.actor.name if credit.actor else credit.credit_name) or UNKNOWN_ACTOR
            primary_names.append(name)
        meta.actor = ",".join(primary_names)

        photos = parse_actor_photos(meta.actor_photo)
        if not photos:
            return
        new_photos: Dict[str, str] = {}
        for credit in credits:
            actor = credit.actor
            if not actor:
                continue
            primary = actor.name
            url = ""
            for key, photo in photos.items():
                if _norm_key(key) in {_norm_key(credit.credit_name), _norm_key(primary)}:
                    url = photo
                    break
            if not url and len(credits) == 1 and len(photos) == 1:
                url = next(iter(photos.values()))
            if url:
                new_photos[primary] = url
        if new_photos:
            meta.actor_photo = json.dumps(new_photos, ensure_ascii=False)

    def rewrite_all_credits_for_actor(self, actor_id: int) -> int:
        """某演员主名变更后，重写其所有相关 Metadata 的写出字段。"""
        meta_ids = [
            row[0]
            for row in (
                self.session.query(MetadataActor.metadata_id)
                .filter(MetadataActor.actor_id == actor_id)
                .distinct()
                .all()
            )
        ]
        for metadata_id in meta_ids:
            self.rewrite_metadata_actor_fields(metadata_id)
        return len(meta_ids)

    def rename_actor(self, actor_id: int, new_name: str) -> Actor:
        """改主名：旧名进别名；按出演回写相关 Metadata.actor。调用方负责 commit。"""
        actor = self.get_by_id(actor_id)
        if not actor:
            raise ValueError("演员不存在")
        text = (new_name or "").strip()
        if not text:
            raise ValueError("主名不能为空")
        if text == UNKNOWN_ACTOR and actor.name != UNKNOWN_ACTOR:
            raise ValueError("不能改名为佚名")

        other = self.find_by_name(text)
        if other and other.id != actor.id:
            raise ValueError(f"名字已被其他人占用: {other.name}")

        old_name = actor.name
        if _norm_key(old_name) != _norm_key(text):
            self.ensure_alias(actor, old_name)
        actor.name = text
        self.ensure_alias(actor, text)
        self.session.flush()
        self.rewrite_all_credits_for_actor(actor.id)
        self.session.flush()
        return self.get_by_id(actor.id) or actor

    def set_aliases(self, actor_id: int, alias_names: List[str]) -> Actor:
        """覆盖别名列表；主名始终保留；冲突名拒绝。调用方负责 commit。"""
        actor = self.get_by_id(actor_id)
        if not actor:
            raise ValueError("演员不存在")

        cleaned: List[str] = []
        seen: Set[str] = set()
        for raw in alias_names or []:
            text = (raw or "").strip()
            if not text:
                continue
            key = _norm_key(text)
            if key in seen or key == _norm_key(actor.name):
                continue
            seen.add(key)
            cleaned.append(text)

        for text in cleaned:
            other = (
                self.session.query(ActorAlias)
                .filter(func.lower(ActorAlias.name) == text.lower())
                .first()
            )
            if other and other.actor_id != actor.id:
                raise ValueError(f"别名已被其他人占用: {text}")

        keep_keys = {_norm_key(actor.name)} | {_norm_key(n) for n in cleaned}
        for alias in list(actor.aliases or []):
            if _norm_key(alias.name) not in keep_keys:
                self.session.delete(alias)
        self.session.flush()

        self.ensure_alias(actor, actor.name)
        for text in cleaned:
            self.ensure_alias(actor, text)
        self.session.flush()
        return self.get_by_id(actor.id) or actor

    def cleanup_orphan_actors(self) -> int:
        """删除没有任何出演关联的演员（别名随 CASCADE 清掉）。"""
        orphans = (
            self.session.query(Actor)
            .outerjoin(MetadataActor, MetadataActor.actor_id == Actor.id)
            .filter(MetadataActor.id.is_(None))
            .all()
        )
        removed = 0
        for actor in orphans:
            self.session.delete(actor)
            removed += 1
        if removed:
            self.session.flush()
        return removed

    def sync_from_metadata(self, cleanup_orphans: bool = False) -> dict:
        """扫描全部 Metadata：写入 Actor / ActorAlias，并重建 metadata_actor。"""
        before_count = self.session.query(Actor).count()
        rows = (
            self.session.query(Metadata)
            .order_by(Metadata.updatetime.desc(), Metadata.id.desc())
            .all()
        )
        name_index = self.load_name_index()
        seen_keys: Set[str] = set()
        credit_rows = 0

        for meta in rows:
            names = split_actor_names(meta.actor)
            for name in names:
                seen_keys.add(_norm_key(name))
            credits = self.replace_credits_for_metadata(
                meta.id,
                meta.actor,
                meta.actor_photo,
                name_index=name_index,
                rewrite=True,
            )
            credit_rows += len(credits)

        removed = self.cleanup_orphan_actors() if cleanup_orphans else 0
        self.session.commit()
        total = self.session.query(Actor).count()
        alias_total = self.session.query(ActorAlias).count()
        created = max(0, total - before_count)
        logger.info(
            "演员回填完成: scanned=%s created=%s removed=%s actors=%s aliases=%s credits=%s",
            len(seen_keys),
            created,
            removed,
            total,
            alias_total,
            credit_rows,
        )
        return {
            "scanned_names": len(seen_keys),
            "created": created,
            "removed": removed,
            "actors": total,
            "aliases": alias_total,
            "credits": credit_rows,
        }

    def tidy_from_metadata(self) -> dict:
        """整理：回填出演关联，并清理无出演的废弃演员。"""
        return self.sync_from_metadata(cleanup_orphans=True)
