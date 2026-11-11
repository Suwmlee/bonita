import io
import logging
import os
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from PIL import Image
from sqlalchemy.orm import Session, joinedload

from bonita.db.models.actor import Actor
from bonita.modules.media_service.emby import EmbyClient
from bonita.modules.media_service.factory import ensure_media_client
from bonita.utils.downloader import cached_filepath

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]


def _norm_name(name: str) -> str:
    return (name or "").strip().casefold()


def _prepare_emby_jpeg(image_path: str) -> bytes:
    """对齐 Gfriends Inputer：转 RGB JPEG 再 base64 上传，避免 P/透明通道导致失败。"""
    with Image.open(image_path) as pic:
        if pic.mode != "RGB":
            pic = pic.convert("RGB")
        buf = io.BytesIO()
        pic.save(buf, format="JPEG", quality=95)
        return buf.getvalue()


class ActorEmbySyncService:
    """把 Bonita 演员头像同步到 Emby Person.Primary。

    以 Bonita 有头像的演员为主循环（通常更少）；上传前转 RGB JPEG。
    """

    def __init__(self, session: Session):
        self.session = session

    def _local_image_path(self, photo: str) -> str:
        """仅用本地已有文件；不下载远程图。"""
        if not photo:
            return ""
        if os.path.isfile(photo):
            return photo
        return cached_filepath(self.session, photo) or ""

    def sync_photos(
        self,
        force: bool = False,
        progress: Optional[ProgressCallback] = None,
    ) -> dict:
        client = ensure_media_client()
        if not isinstance(client, EmbyClient):
            raise RuntimeError("Emby服务未初始化或未启用")

        actors = (
            self.session.query(Actor)
            .options(joinedload(Actor.aliases))
            .filter(Actor.photo.isnot(None), Actor.photo != "")
            .order_by(Actor.id.asc())
            .all()
        )
        # 先滤掉无本地缓存的，主循环更短
        ready: List[tuple[Actor, str]] = []
        no_local = 0
        for actor in actors:
            path = self._local_image_path((actor.photo or "").strip())
            if path:
                ready.append((actor, path))
            else:
                no_local += 1

        logger.info(
            "Bonita 有 photo 字段 %s 人，本地已缓存 %s，无本地跳过 %s；拉取 Emby 人物…",
            len(actors),
            len(ready),
            no_local,
        )
        if progress:
            progress(
                5.0,
                f"本地可上传 {len(ready)}/{len(actors)}，拉取 Emby 人物列表…",
            )

        persons = client.list_persons()
        by_name: Dict[str, List[dict]] = defaultdict(list)
        for person in persons:
            if not isinstance(person, dict):
                continue
            key = _norm_name(person.get("Name") or "")
            if not key:
                continue
            by_name[key].append(person)

        logger.info("Emby 人物 %s，开始按 Bonita 演员上传", len(persons))
        if progress:
            progress(15.0, f"Emby 人物 {len(persons)}，开始上传…")

        scanned = 0
        uploaded = 0
        skipped = 0
        missing = 0
        failed = 0
        total = max(len(ready), 1)

        for actor, image_path in ready:
            scanned += 1
            names = [actor.name] + [alias.name for alias in (actor.aliases or [])]
            matched: Dict[str, dict] = {}
            for name in names:
                key = _norm_name(name)
                if not key:
                    continue
                for person in by_name.get(key, []):
                    person_id = str(person.get("Id") or "").strip()
                    if person_id:
                        matched[person_id] = person

            pct = 15.0 + scanned / total * 80.0
            if progress:
                progress(
                    pct,
                    (
                        f"{scanned}/{len(ready)} {actor.name} · "
                        f"上传{uploaded} 跳过{skipped} 无本地{no_local} "
                        f"未匹配{missing} 失败{failed}"
                    ),
                )

            if not matched:
                missing += 1
                logger.info("[%s/%s] 未匹配 Emby 人物: %s", scanned, len(ready), actor.name)
                continue

            try:
                image_bytes = _prepare_emby_jpeg(image_path)
                if not image_bytes:
                    failed += 1
                    logger.warning("头像转 JPEG 失败: %s path=%s", actor.name, image_path)
                    continue

                for person_id, person in matched.items():
                    emby_name = (person.get("Name") or "").strip() or person_id
                    image_tags = person.get("ImageTags") or {}
                    has_primary = bool(image_tags.get("Primary"))
                    if has_primary and not force:
                        skipped += 1
                        logger.info(
                            "跳过（Emby 已有头像）: 演员=%s → Emby=%s id=%s",
                            actor.name,
                            emby_name,
                            person_id,
                        )
                        continue
                    try:
                        client.upload_item_image(
                            person_id,
                            image_bytes,
                            image_type="Primary",
                            content_type="image/jpeg",
                        )
                        uploaded += 1
                        logger.info(
                            "已更新头像: 演员=%s → Emby=%s id=%s",
                            actor.name,
                            emby_name,
                            person_id,
                        )
                    except Exception as exc:
                        failed += 1
                        logger.warning(
                            "上传失败: 演员=%s → Emby=%s id=%s: %s",
                            actor.name,
                            emby_name,
                            person_id,
                            exc,
                        )
            except Exception as exc:
                failed += 1
                logger.warning("同步演员头像失败 actor=%s: %s", actor.name, exc)

        result = {
            "scanned": scanned,
            "uploaded": uploaded,
            "skipped": skipped,
            "no_local": no_local,
            "missing": missing,
            "failed": failed,
            "persons": len(persons),
            "force": bool(force),
        }
        if progress:
            progress(100.0, "演员头像同步完成")
        logger.info(
            "演员头像同步完成: scanned=%s uploaded=%s skipped=%s no_local=%s missing=%s failed=%s persons=%s force=%s",
            scanned,
            uploaded,
            skipped,
            no_local,
            missing,
            failed,
            len(persons),
            force,
        )
        return result
