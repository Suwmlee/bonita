import json
import logging
from collections import defaultdict, deque
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
    """演员词典与出演关联：别名认人（同名取作品数最多），metadata_actor 用 id 挂片，写出用主名。"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, actor_id: int) -> Optional[Actor]:
        return (
            self.session.query(Actor)
            .options(joinedload(Actor.aliases))
            .filter(Actor.id == actor_id)
            .first()
        )

    def _work_counts(self, actor_ids: Optional[List[int]] = None) -> Dict[int, int]:
        query = self.session.query(
            MetadataActor.actor_id,
            func.count(func.distinct(MetadataActor.metadata_id)),
        ).group_by(MetadataActor.actor_id)
        if actor_ids is not None:
            if not actor_ids:
                return {}
            query = query.filter(MetadataActor.actor_id.in_(actor_ids))
        return {int(actor_id): int(count) for actor_id, count in query.all()}

    def find_by_name(self, name: str) -> Optional[Actor]:
        """按主名或别名匹配；同名多人时取出演作品数最多（并列取 id 较小）。"""
        matches = self.find_all_by_name(name)
        return matches[0] if matches else None

    def _actors_by_name(self, name: str) -> tuple[List[Actor], Dict[int, int]]:
        text = (name or "").strip()
        if not text:
            return [], {}
        rows = (
            self.session.query(Actor)
            .options(joinedload(Actor.aliases))
            .join(ActorAlias, ActorAlias.actor_id == Actor.id)
            .filter(func.lower(ActorAlias.name) == text.lower())
            .all()
        )
        seen: Set[int] = set()
        result: List[Actor] = []
        for actor in rows:
            if actor.id in seen:
                continue
            seen.add(actor.id)
            result.append(actor)
        counts = self._work_counts([actor.id for actor in result])
        result.sort(key=lambda actor: (-counts.get(actor.id, 0), actor.id))
        return result, counts

    def find_all_by_name(self, name: str) -> List[Actor]:
        """同名（主名或别名）全部演员，按作品数降序、id 升序。"""
        actors, _ = self._actors_by_name(name)
        return actors

    def load_name_index(self) -> Dict[str, Actor]:
        """别名/主名 casefold → Actor；同名取作品数最多（并列 id 较小）。"""
        index: Dict[str, Actor] = {}
        actors = (
            self.session.query(Actor)
            .options(joinedload(Actor.aliases))
            .all()
        )
        counts = self._work_counts([actor.id for actor in actors])
        actors.sort(key=lambda actor: (-counts.get(actor.id, 0), actor.id))
        for actor in actors:
            key = _norm_key(actor.name)
            if key not in index:
                index[key] = actor
            for alias in actor.aliases:
                akey = _norm_key(alias.name)
                if akey not in index:
                    index[akey] = actor
        return index

    def alias_names_of(self, actor: Actor) -> Set[str]:
        names = {_norm_key(actor.name)}
        for alias in actor.aliases or []:
            names.add(_norm_key(alias.name))
        return names

    def ensure_alias(self, actor: Actor, name: str) -> bool:
        """追加别名；同一人已有精确同名或大小写变体则跳过。允许与他人同名。"""
        text = (name or "").strip()
        if not text:
            return False
        same = (
            self.session.query(ActorAlias)
            .filter(
                ActorAlias.actor_id == actor.id,
                func.lower(ActorAlias.name) == text.lower(),
            )
            .first()
        )
        if same:
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
        """确保名字对应的演员存在；同名取作品数最多的，不自动新建第二个。"""
        text = (name or "").strip() or UNKNOWN_ACTOR
        photo_url = (photo or "").strip()
        index = name_index if name_index is not None else self.load_name_index()
        key = _norm_key(text)
        actor = index.get(key)
        if actor:
            if photo_url and not (actor.photo or "").strip():
                actor.photo = photo_url
            self.ensure_alias(actor, text)
            return actor

        actor = Actor(name=text, photo=photo_url or "")
        self.session.add(actor)
        self.session.flush()
        self.session.add(ActorAlias(actor_id=actor.id, name=text))
        self.session.flush()
        index[key] = actor
        return actor

    def _photo_for_name(
        self,
        name: str,
        photos: Dict[str, str],
        only_one: bool,
    ) -> Optional[str]:
        key = _norm_key(name)
        for photo_key, url in photos.items():
            if _norm_key(photo_key) == key:
                return url
        if only_one and len(photos) == 1:
            return next(iter(photos.values()))
        return None

    def replace_credits_for_metadata(
        self,
        metadata_id: int,
        actor_field: Optional[str],
        actor_photo_field: Optional[str] = None,
        name_index: Optional[Dict[str, Actor]] = None,
        rewrite: bool = True,
    ) -> List[MetadataActor]:
        """按当前演员字段重写该片出演行。

        优先保留已挂的 actor_id（避免新建同名后被 sync/保存冲回作品数最多的同名）。
        """
        names = split_actor_names(actor_field)
        photos = parse_actor_photos(actor_photo_field)
        only_one = len(names) == 1
        index = name_index if name_index is not None else self.load_name_index()

        old_credits = (
            self.session.query(MetadataActor)
            .options(joinedload(MetadataActor.actor).joinedload(Actor.aliases))
            .filter(MetadataActor.metadata_id == metadata_id)
            .order_by(MetadataActor.sort.asc(), MetadataActor.id.asc())
            .all()
        )
        # 按 credit_name 与当前演员主名/别名都登记，避免回写主名后保存冲掉同名改挂
        reserved: Dict[str, deque] = defaultdict(deque)
        for credit in old_credits:
            keys = {_norm_key(credit.credit_name)}
            if credit.actor:
                keys |= self.alias_names_of(credit.actor)
            for key in keys:
                if key:
                    reserved[key].append(credit.actor_id)

        self.session.query(MetadataActor).filter(
            MetadataActor.metadata_id == metadata_id
        ).delete(synchronize_session=False)

        credits: List[MetadataActor] = []
        seen_ids: Set[int] = set()
        sort = 0
        for name in names:
            key = _norm_key(name)
            actor: Optional[Actor] = None
            while reserved[key]:
                aid = reserved[key].popleft()
                cand = self.get_by_id(aid)
                if cand and key in self.alias_names_of(cand) and cand.id not in seen_ids:
                    actor = cand
                    break
            photo = self._photo_for_name(name, photos, only_one)
            if actor is None:
                actor = self.ensure_actor(name, photo, name_index=index)
            else:
                photo_url = (photo or "").strip()
                if photo_url and not (actor.photo or "").strip():
                    actor.photo = photo_url
                self.ensure_alias(actor, name)

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
        """覆盖别名列表；主名始终保留；允许与他人同名。调用方负责 commit。"""
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

    def list_homonyms(self, name: str) -> List[dict]:
        """同名候选：按作品数降序。"""
        actors, counts = self._actors_by_name(name)
        return [
            {
                "id": actor.id,
                "name": actor.name,
                "photo": (actor.photo or "").strip() or None,
                "count": counts.get(actor.id, 0),
            }
            for actor in actors
        ]

    def list_credits_for_metadata(self, metadata_id: int) -> List[dict]:
        """某片出演行，附带同名人数。"""
        credits = (
            self.session.query(MetadataActor)
            .options(joinedload(MetadataActor.actor).joinedload(Actor.aliases))
            .filter(MetadataActor.metadata_id == metadata_id)
            .order_by(MetadataActor.sort.asc(), MetadataActor.id.asc())
            .all()
        )
        result = []
        for credit in credits:
            actor = credit.actor
            name_for_homonym = (actor.name if actor else credit.credit_name) or ""
            homonyms = self.find_all_by_name(name_for_homonym) if name_for_homonym else []
            result.append(
                {
                    "actor_id": credit.actor_id,
                    "actor_name": actor.name if actor else credit.credit_name,
                    "credit_name": credit.credit_name,
                    "sort": credit.sort,
                    "photo": ((actor.photo or "").strip() or None) if actor else None,
                    "homonym_count": len(homonyms),
                }
            )
        return result

    def rematch_credit(
        self,
        metadata_id: int,
        from_actor_id: int,
        to_actor_id: int,
    ) -> List[dict]:
        """只改挂这一行出演到已有演员。"""
        if from_actor_id == to_actor_id:
            return self.list_credits_for_metadata(metadata_id)
        credit = (
            self.session.query(MetadataActor)
            .filter(
                MetadataActor.metadata_id == metadata_id,
                MetadataActor.actor_id == from_actor_id,
            )
            .first()
        )
        if not credit:
            raise ValueError("该片没有这位演员的出演记录")
        target = self.get_by_id(to_actor_id)
        if not target:
            raise ValueError("目标演员不存在")
        exists = (
            self.session.query(MetadataActor)
            .filter(
                MetadataActor.metadata_id == metadata_id,
                MetadataActor.actor_id == to_actor_id,
            )
            .first()
        )
        if exists:
            raise ValueError("目标演员已在该片出演，无法改挂")
        credit.actor_id = to_actor_id
        self.session.flush()
        self.rewrite_metadata_actor_fields(metadata_id)
        self.session.flush()
        return self.list_credits_for_metadata(metadata_id)

    def split_credit_to_new_actor(
        self,
        metadata_id: int,
        from_actor_id: int,
        new_name: Optional[str] = None,
    ) -> dict:
        """新建同名演员，只改挂这一行。"""
        credit = (
            self.session.query(MetadataActor)
            .options(joinedload(MetadataActor.actor))
            .filter(
                MetadataActor.metadata_id == metadata_id,
                MetadataActor.actor_id == from_actor_id,
            )
            .first()
        )
        if not credit:
            raise ValueError("该片没有这位演员的出演记录")
        source = credit.actor or self.get_by_id(from_actor_id)
        text = (new_name or (source.name if source else "") or credit.credit_name or "").strip()
        if not text:
            raise ValueError("新演员主名不能为空")
        if text == UNKNOWN_ACTOR:
            raise ValueError("不能新建为佚名")

        # 不复制头像，避免同名新人与原演员无法区分
        actor = Actor(name=text, photo="")
        self.session.add(actor)
        self.session.flush()
        self.session.add(ActorAlias(actor_id=actor.id, name=text))
        self.session.flush()

        credit.actor_id = actor.id
        self.session.flush()
        self.rewrite_metadata_actor_fields(metadata_id)
        self.session.flush()
        return {
            "actor": actor,
            "credits": self.list_credits_for_metadata(metadata_id),
        }

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
