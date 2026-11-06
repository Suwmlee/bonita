import filecmp
import json
import logging
import os
import re
import shutil
import stat
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, aliased

from bonita.core.config import settings
from bonita.db.models.mediaitem import MediaItem
from bonita.db.models.record import TransRecords
from bonita.db.models.subtitle import Subtitle
from bonita.modules.scraping.number_parser import FileNumInfo, rules_parser
from bonita.utils.filehelper import subext_type

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "zh-Hans"
CHINESE_LANGUAGES = ("zh-Hans", "zh-Hant")
SUPPORTED_LANGUAGES = ("zh-Hans", "zh-Hant", "en")

_LANG_RULES = (
    (re.compile(r"(?:^|[.\-_])(?:zh[-_]?hant|zht|cht|zh[-_]?tw)(?=$|[.\-_])", re.I), "zh-Hant"),
    (re.compile(r"(?:^|[.\-_])(?:zh[-_]?hans|zhs|chs|zh[-_]?cn|chi|chn)(?=$|[.\-_])", re.I), "zh-Hans"),
    (re.compile(r"(?:^|[.\-_])(?:eng|en)(?=$|[.\-_])", re.I), "en"),
    (re.compile(r"(?:^|[.\-_])(?:tc)(?=$|[.\-_])", re.I), "zh-Hant"),
    (re.compile(r"(?:^|[.\-_])(?:sc|zh|cn|c)(?=$|[.\-_])", re.I), "zh-Hans"),
)

_DELIVER_SUFFIX = {
    "zh-Hans": ".chs",
    "zh-Hant": ".cht",
    "en": ".en",
}

_FILE_MODE = stat.S_IRWXU | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
_BINDABLE_TYPES = {"movie", "video", "number", "episode"}


def normalize_number(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip().upper()


def has_preferred_chinese_subtitle(
    session,
    number: Optional[str] = None,
    part: int = 0,
    media_item_id: Optional[int] = None,
) -> bool:
    """ 这一部、这一部次有没有在用的简体或繁体字幕。 """
    query = session.query(Subtitle.id).filter(
        Subtitle.preferred.is_(True),
        Subtitle.part_number == int(part or 0),
        Subtitle.language.in_(CHINESE_LANGUAGES),
    )
    if media_item_id:
        query = query.filter(Subtitle.media_item_id == media_item_id)
    else:
        key = normalize_number(number)
        if not key:
            return False
        query = query.join(MediaItem, MediaItem.id == Subtitle.media_item_id).filter(
            func.upper(func.trim(MediaItem.number)) == key
        )
    return query.first() is not None


def normalize_language(value: Optional[str]) -> str:
    language = (value or "").strip()
    if language in SUPPORTED_LANGUAGES:
        return language
    return DEFAULT_LANGUAGE


def parse_language(filename: str) -> str:
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    for pattern, language in _LANG_RULES:
        if pattern.search(stem):
            return language
    return DEFAULT_LANGUAGE


def parse_part(filename: str) -> int:
    try:
        part = FileNumInfo.checkPart(os.path.basename(filename or ""))
    except Exception:
        return 0
    return int(part or 0)


def parse_number(filename: str) -> str:
    basename = os.path.basename(filename or "")
    stem = os.path.splitext(basename)[0]
    parent = os.path.basename(os.path.dirname(filename or ""))
    for candidate in (stem, basename, parent):
        if not candidate:
            continue
        try:
            found = rules_parser(candidate)
        except Exception:
            logger.debug("parse subtitle number failed: %s", candidate, exc_info=True)
            found = None
        if found:
            return normalize_number(found)
    return ""


def deliver_suffix(language: str) -> str:
    return _DELIVER_SUFFIX.get(normalize_language(language), ".chs")


def dest_subtitle_path(video_path: str, language: str, extension: str) -> str:
    folder = os.path.dirname(video_path)
    stem = os.path.splitext(os.path.basename(video_path))[0]
    ext = extension if str(extension).startswith(".") else f".{extension}"
    return os.path.join(folder, f"{stem}{deliver_suffix(language)}{ext}")


def target_visible(path: str) -> bool:
    """目录列举里真有这个文件。网络盘的 stat 缓存有时会把已删除文件报成存在。"""
    folder = os.path.dirname(path) or "."
    name = os.path.basename(path)
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.name != name:
                    continue
                try:
                    return entry.is_file(follow_symlinks=True)
                except OSError:
                    return False
    except OSError:
        return False
    return False


def same_subtitle(source: str, target: str) -> bool:
    if not target_visible(target):
        return False
    try:
        return filecmp.cmp(source, target, shallow=False)
    except OSError:
        return False


def source_is_newer(source: str, target: str) -> bool:
    try:
        return os.stat(source).st_mtime > os.stat(target).st_mtime + 1
    except OSError:
        return False


def safe_filename(name: str, extension: str) -> str:
    """保留上传时的文件名，只去掉路径分隔符。"""
    base = os.path.basename(name or "").replace("\x00", "").strip()
    base = re.sub(r"[\\/]+", "_", base).strip(" .")
    ext = extension if str(extension).startswith(".") else f".{extension}" if extension else ""
    if not base:
        base = f"subtitle{ext or '.srt'}"
    elif ext and not base.lower().endswith(ext.lower()):
        base = f"{base}{ext}"
    stem, found = os.path.splitext(base)
    if len(base) > 180:
        base = f"{stem[:180 - len(found)]}{found}"
    return base or "subtitle.srt"


def load_delivered_paths(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, str) and item.strip()]


def dump_delivered_paths(paths: List[str]) -> str:
    unique = []
    seen = set()
    for path in paths:
        norm = os.path.normpath(path)
        if norm in seen:
            continue
        seen.add(norm)
        unique.append(norm)
    if not unique:
        return ""
    return json.dumps(unique, ensure_ascii=False)


def safe_storage_key(number: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (number or "").strip())
    cleaned = cleaned.strip("._")
    return cleaned or "unknown"


def subtitle_group_id(
    media_type: Optional[str],
    series_id: Optional[int],
    media_item_id: Optional[int],
) -> Optional[int]:
    """单集归到所属剧，其余归到字幕自己的媒体项。"""
    if media_type == "episode" and series_id:
        return series_id
    return media_item_id


def _group_id_expr(file_item):
    """SQL 分组键，条件和 subtitle_group_id 一致。"""
    return case(
        (
            and_(file_item.media_type == "episode", file_item.series_id.isnot(None)),
            file_item.series_id,
        ),
        else_=Subtitle.media_item_id,
    )


class SubtitleService:
    def __init__(self, session: Session):
        self.session = session

    def _filtered_query(
        self,
        filter_text: Optional[str] = None,
        unmatched: bool = False,
        media_item_id: Optional[int] = None,
    ):
        file_item = aliased(MediaItem)
        series_item = aliased(MediaItem)
        group_id = _group_id_expr(file_item)
        query = (
            self.session.query(Subtitle)
            .outerjoin(file_item, Subtitle.media_item_id == file_item.id)
            .outerjoin(series_item, series_item.id == file_item.series_id)
        )
        if media_item_id:
            query = query.filter(Subtitle.media_item_id == media_item_id)
        elif unmatched:
            query = query.filter(Subtitle.media_item_id.is_(None))
        if filter_text:
            like = f"%{filter_text.strip()}%"
            query = query.filter(or_(
                Subtitle.original_name.like(like),
                file_item.number.like(like),
                file_item.title.like(like),
                file_item.original_title.like(like),
                file_item.imdb_id.like(like),
                series_item.title.like(like),
                series_item.original_title.like(like),
                series_item.imdb_id.like(like),
            ))
        return query, group_id

    def list_subtitles(
        self,
        skip: int = 0,
        limit: int = 50,
        filter_text: Optional[str] = None,
        unmatched: bool = False,
        media_item_id: Optional[int] = None,
    ) -> Tuple[List[Subtitle], int]:
        query, _group_id = self._filtered_query(filter_text, unmatched, media_item_id)
        count = query.count()
        rows = query.order_by(Subtitle.updatetime.desc(), Subtitle.id.desc()).offset(skip).limit(limit).all()
        return rows, count

    def list_groups(
        self,
        skip: int = 0,
        limit: int = 20,
        filter_text: Optional[str] = None,
        unmatched: bool = False,
    ) -> Tuple[list, int]:
        matched, group_id = self._filtered_query(filter_text, unmatched)
        grouped = (
            matched.with_entities(
                group_id.label("group_id"),
                func.max(Subtitle.updatetime).label("latest"),
            )
            .group_by(group_id)
            .order_by(func.max(Subtitle.updatetime).desc())
        )
        total = grouped.order_by(None).count()
        page = grouped.offset(skip).limit(limit).all()
        ids = [row.group_id for row in page if row.group_id]
        include_unmatched = any(row.group_id is None for row in page)
        clauses = []
        if ids:
            clauses.append(group_id.in_(ids))
        if include_unmatched:
            clauses.append(group_id.is_(None))
        rows = []
        if clauses:
            rows = (
                matched.filter(or_(*clauses))
                .order_by(Subtitle.updatetime.desc(), Subtitle.id.desc())
                .all()
            )
        bucket = {}
        for row in rows:
            bucket.setdefault(self._row_group_id(row), []).append(row)
        groups = [
            self._group_payload(row.group_id, bucket.get(row.group_id, []))
            for row in page
        ]
        return groups, total

    def _row_group_id(self, row: Subtitle) -> Optional[int]:
        item = self._cached_item(row.media_item_id)
        if not item:
            return subtitle_group_id(None, None, row.media_item_id)
        return subtitle_group_id(item.media_type, item.series_id, row.media_item_id)

    def _subtitle_sort_key(self, row: Subtitle):
        item = self._cached_item(row.media_item_id)
        updated = row.updatetime.timestamp() if row.updatetime else 0
        if item and item.media_type == "episode":
            season = item.season_number if isinstance(item.season_number, int) and item.season_number >= 0 else 10**6
            episode = item.episode_number if isinstance(item.episode_number, int) and item.episode_number >= 0 else 10**6
            return (0, season, episode, int(row.part_number or 0), row.language or "", row.id or 0)
        return (1, -updated, int(row.part_number or 0), row.language or "", row.id or 0)

    def _group_payload(self, media_item_id: Optional[int], rows: List[Subtitle]) -> dict:
        item = self._cached_item(media_item_id)
        rows = sorted(rows, key=self._subtitle_sort_key)
        number = ""
        if item and item.number and item.media_type in ("number", "movie", "video"):
            number = normalize_number(item.number)
        meta = None
        if number and item and item.media_type == "number":
            from bonita.modules.media_service.record_link import metadata_for_number
            meta = metadata_for_number(self.session, number)
        title = ""
        if meta and (meta.title or "").strip():
            title = meta.title.strip()
        elif item and item.title and normalize_number(item.title) != number:
            title = item.title
        return {
            "key": str(media_item_id) if media_item_id else "unmatched",
            "media_item_id": media_item_id,
            "media_type": item.media_type if item else "",
            "number": number,
            "title": title,
            "imdb_id": (item.imdb_id or "") if item else "",
            "tmdb_id": (item.tmdb_id or "") if item else "",
            "crop": self._group_crop(number),
            "count": len(rows),
            "subtitles": [self.describe(row) for row in rows],
        }

    def _group_crop(self, number: str) -> bool:
        if not number:
            return False
        from bonita.services.metadata_service import MetadataService

        return MetadataService(self.session).resolve_crop(number)

    def describe(self, row: Subtitle, item: Optional[MediaItem] = None) -> dict:
        data = row.to_dict()
        data.pop("delivered_paths", None)
        data.pop("stored_path", None)
        data["preferred"] = bool(row.preferred)
        try:
            path = self._absolute(row.stored_path) if row.stored_path else ""
        except ValueError:
            path = ""
        file_size = None
        if path and os.path.isfile(path):
            try:
                file_size = os.path.getsize(path)
            except OSError:
                file_size = None
        data["file_size"] = file_size
        if row.media_item_id:
            if item is None or item.id != row.media_item_id:
                item = self._cached_item(row.media_item_id)
        else:
            item = None
        series_title = ""
        if item and item.media_type == "episode" and item.series_id:
            series = self._cached_item(item.series_id)
            if series:
                series_title = series.title or ""
        data["media_item_id"] = row.media_item_id
        data["media_type"] = item.media_type if item else ""
        data["number"] = (item.number or "") if item else ""
        data["title"] = (item.title or "") if item else ""
        data["series_title"] = series_title
        data["season_number"] = item.season_number if item else None
        data["episode_number"] = item.episode_number if item else None
        return data

    def _cached_item(self, item_id: Optional[int]) -> Optional[MediaItem]:
        if not item_id:
            return None
        cache = self.__dict__.setdefault("_item_cache", {})
        if item_id not in cache:
            cache[item_id] = self.session.get(MediaItem, item_id)
        return cache[item_id]

    def get(self, subtitle_id: int) -> Optional[Subtitle]:
        return self.session.get(Subtitle, subtitle_id)

    def counts_for(self, pairs: List[Tuple[Optional[int], int]]) -> dict:
        ids = {item_id for item_id, _part in pairs if item_id}
        if not ids:
            return {}
        rows = (
            self.session.query(Subtitle.media_item_id, Subtitle.part_number, func.count(Subtitle.id))
            .filter(Subtitle.media_item_id.in_(ids))
            .group_by(Subtitle.media_item_id, Subtitle.part_number)
            .all()
        )
        return {(item_id, part or 0): count for item_id, part, count in rows}

    def save_bytes(
        self,
        filename: str,
        content: bytes,
        number: Optional[str] = None,
        media_item_id: Optional[int] = None,
    ) -> dict:
        original_name = os.path.basename(filename or "").strip()
        if not original_name:
            raise ValueError("缺少文件名")
        extension = os.path.splitext(original_name)[1].lower()
        if extension not in subext_type:
            raise ValueError(f"不支持的字幕格式: {original_name}")
        if not content:
            raise ValueError(f"文件为空: {original_name}")

        item = self._resolve_upload_item(original_name, number, media_item_id)
        language = parse_language(original_name)
        part_number = parse_part(original_name)
        now = datetime.now()

        existing_query = self.session.query(Subtitle).filter(Subtitle.original_name == original_name)
        if item:
            existing_query = existing_query.filter(Subtitle.media_item_id == item.id)
        else:
            existing_query = existing_query.filter(Subtitle.media_item_id.is_(None))
        existing = existing_query.order_by(Subtitle.id.desc()).first()

        if existing:
            old_group = self._group_key(existing)
            was_preferred = bool(existing.preferred)
            relative = self._storage_relative(item, original_name, extension)
            self._write(relative, content)
            self._remove_file(existing.stored_path, keep=relative)
            existing.media_item_id = item.id if item else None
            existing.original_name = original_name
            existing.language = language
            existing.part_number = part_number
            existing.file_extension = extension
            existing.stored_path = relative
            existing.updatetime = now
            self._place_in_group(existing, old_group, was_preferred)
            self.session.commit()
            self._follow_group_change(existing, old_group, was_preferred)
            return {"subtitle": existing, "replaced": True, "unmatched": item is None}

        relative = self._storage_relative(item, original_name, extension)
        self._write(relative, content)
        row = Subtitle(
            media_item_id=item.id if item else None,
            language=language,
            part_number=part_number,
            original_name=original_name,
            stored_path=relative,
            file_extension=extension,
            preferred=False,
            delivered_paths="",
            createtime=now,
            updatetime=now,
        )
        row.create(self.session)
        if item and self._preferred_other(item.id, language, part_number, row.id) is None:
            row.preferred = True
            self.session.commit()
        return {"subtitle": row, "replaced": False, "unmatched": item is None}

    def update_subtitle(
        self,
        subtitle_id: int,
        number: str,
        language: str,
        part_number: int,
        media_item_id: Optional[int] = None,
    ) -> Optional[Subtitle]:
        row = self.get(subtitle_id)
        if not row:
            return None
        old_group = self._group_key(row)
        was_preferred = bool(row.preferred)
        if media_item_id:
            item = self.session.get(MediaItem, int(media_item_id))
            if not item or item.media_type not in _BINDABLE_TYPES:
                raise ValueError("请选择具体的电影、单集或番号")
        else:
            key = normalize_number(number)
            item = self._resolve_number_item(key) if key else None
            if key and not item:
                raise ValueError("没有对应的媒体项")
        language = normalize_language(language)
        part_number = int(part_number or 0)
        extension = row.file_extension or os.path.splitext(row.original_name or "")[1].lower()
        relative = self._storage_relative(item, row.original_name or "", extension)
        self._move_stored(row.stored_path, relative)
        row.media_item_id = item.id if item else None
        row.language = language
        row.part_number = part_number
        row.file_extension = extension
        row.stored_path = relative
        row.updatetime = datetime.now()
        self._place_in_group(row, old_group, was_preferred)
        self.session.commit()
        self._follow_group_change(row, old_group, was_preferred)
        return row

    def delete_subtitle(self, subtitle_id: int) -> bool:
        row = self.get(subtitle_id)
        if not row:
            return False
        media_item_id, language, part = self._group_key(row)
        was_preferred = bool(row.preferred)
        if was_preferred:
            self._release(row)
        self._remove_file(row.stored_path)
        self.session.delete(row)
        self.session.commit()
        if was_preferred and media_item_id:
            try:
                self._promote_if_single(media_item_id, language, part)
            except Exception:
                logger.exception("删除字幕后同步影片旁边的文件失败: %s", media_item_id)
        return True

    def detach_for_deleted_items(self, media_item_ids: List[int]) -> None:
        """媒体项删除后，挂在上面的字幕改为未关联，并取消在用。不提交。"""
        ids = [item_id for item_id in media_item_ids if item_id]
        if not ids:
            return
        rows = self.session.query(Subtitle).filter(Subtitle.media_item_id.in_(ids)).all()
        now = datetime.now()
        for row in rows:
            if row.preferred:
                try:
                    self._release(row)
                except Exception:
                    logger.exception("删除媒体项后清理已投递字幕失败: %s", row.id)
                    row.preferred = False
            row.media_item_id = None
            row.preferred = False
            row.updatetime = now

    def deliver_subtitle(self, subtitle_id: int, overwrite: bool = False):
        row = self.get(subtitle_id)
        if not row:
            return None
        if not row.media_item_id:
            raise ValueError("字幕尚未关联媒体项")
        if not row.preferred:
            raise ValueError("这份不是当前使用的字幕")
        return self._deliver_rows([row], overwrite=overwrite)

    def use_subtitle(self, subtitle_id: int, overwrite: bool = False):
        """把这一份标成在用，清掉原来那份记下的文件，再投递。"""
        row = self.get(subtitle_id)
        if not row:
            return None
        if not row.media_item_id:
            raise ValueError("字幕尚未关联媒体项")
        details = []
        others = (
            self._group_query(row.media_item_id, row.language or "", int(row.part_number or 0))
            .filter(Subtitle.id != row.id, Subtitle.preferred.is_(True))
            .all()
        )
        for other in others:
            details.extend(self._release(other))
        row.preferred = True
        self.session.commit()
        result = self._deliver_rows([row], overwrite=overwrite)
        result["details"] = details + result["details"]
        return result

    def deliver_items(
        self,
        media_item_ids: List[int],
        part_number: Optional[int] = None,
        overwrite: bool = False,
    ) -> dict:
        ids = [item_id for item_id in media_item_ids if item_id]
        if not ids:
            raise ValueError("缺少媒体项")
        query = self.session.query(Subtitle).filter(Subtitle.media_item_id.in_(ids))
        if part_number is not None:
            query = query.filter(Subtitle.part_number == part_number)
        return self._deliver_rows(query.all(), overwrite=overwrite)

    def retransfer_matches(self, media_item_id: Optional[int], part_number: int = 0) -> int:
        """重新转移挂着这个媒体项、这部次的记录。刮削开着时会重写海报和 NFO，结束后再投递在用字幕。"""
        if not media_item_id:
            return 0
        part = int(part_number or 0)
        query = self.session.query(TransRecords.task_id, TransRecords.srcpath).filter(
            TransRecords.media_item_id == media_item_id,
            TransRecords.deleted.is_(False),
            TransRecords.ignored.is_(False),
            TransRecords.srcdeleted.is_(False),
            TransRecords.task_id.isnot(None),
            TransRecords.srcpath.isnot(None),
            TransRecords.srcpath != "",
        )
        if part == 0:
            query = query.filter(or_(TransRecords.part_number == 0, TransRecords.part_number.is_(None)))
        else:
            query = query.filter(TransRecords.part_number == part)
        from bonita.services.transfer_config_service import TransferConfigService

        service = TransferConfigService(self.session)
        seen = set()
        started = 0
        for task_id, srcpath in query.all():
            key = (task_id, os.path.normpath(srcpath))
            if key in seen:
                continue
            seen.add(key)
            if service.run_transfer(task_id, srcpath):
                started += 1
        return started

    def deliver_for_transfer(
        self,
        destpath: str,
        part_number: int = 0,
        media_item_id: Optional[int] = None,
        number: Optional[str] = None,
    ) -> int:
        """转移完成后，把在用字幕复制到这次的目标文件旁边。

        有媒体项时按媒体项找。没有时用番号找到已有的番号媒体项再投递。
        """
        item_id = media_item_id or self._item_id_for_number(number)
        if not destpath or not item_id:
            return 0
        part = int(part_number or 0)
        rows = (
            self.session.query(Subtitle)
            .filter(
                Subtitle.media_item_id == item_id,
                Subtitle.part_number == part,
            )
            .all()
        )
        if rows and not any(row.preferred for row in rows):
            logger.info("字幕投递跳过：媒体项 %s 部次 %s 没有标成在用的字幕", item_id, part)
            return 0
        return self._deliver_rows(rows, only_path=destpath)["copied"]

    def _item_id_for_number(self, number: Optional[str]) -> Optional[int]:
        key = normalize_number(number)
        if not key:
            return None
        from bonita.modules.media_service.record_link import find_number_media_item

        item = find_number_media_item(self.session, key)
        return item.id if item else None

    def _deliver_rows(self, rows: List[Subtitle], overwrite: bool = False, only_path: Optional[str] = None) -> dict:
        result = {"copied": 0, "skipped": 0, "missing": 0, "failed": 0, "details": []}
        rows = [row for row in rows if row.preferred and row.media_item_id]
        if not rows:
            return result
        item_ids = {row.media_item_id for row in rows}
        records = self._records_for_items(item_ids)
        seen = set()
        for row in rows:
            targets = []
            for destpath, media_item_id, part in records:
                if media_item_id != row.media_item_id or int(part or 0) != int(row.part_number or 0):
                    continue
                marker = (row.id, os.path.normpath(destpath))
                if marker in seen:
                    continue
                seen.add(marker)
                targets.append(destpath)
            if only_path:
                targets = [only_path]
            if not targets:
                detail = f"没有可投递的视频：{self._row_label(row)}"
                logger.info("字幕投递缺失：%s", detail)
                result["missing"] += 1
                result["details"].append(detail)
                continue
            written = []
            hold_dirs = set()
            for destpath in targets:
                status, detail, target = self._copy_to_video(row, destpath, overwrite=overwrite)
                result[status] += 1
                if detail:
                    result["details"].append(detail)
                if status in ("copied", "skipped") and target:
                    written.append(target)
                elif destpath:
                    hold_dirs.add(os.path.dirname(os.path.normpath(destpath)))
            limit_dirs = None
            if only_path:
                limit_dirs = {os.path.dirname(os.path.normpath(only_path))}
            for removed in self._settle_paths(row, written, hold_dirs, limit_dirs):
                logger.info("字幕投递清理：%s", removed)
                result["details"].append(removed)
        self.session.commit()
        return result

    def _group_key(self, row: Subtitle):
        return (
            row.media_item_id or None,
            row.language or "",
            int(row.part_number or 0),
        )

    def _group_query(self, media_item_id: Optional[int], language: str, part: int):
        query = self.session.query(Subtitle).filter(
            Subtitle.language == (language or ""),
            Subtitle.part_number == int(part or 0),
        )
        if not media_item_id:
            return query.filter(Subtitle.id == -1)
        return query.filter(Subtitle.media_item_id == media_item_id)

    def _preferred_other(self, media_item_id: Optional[int], language: str, part: int, exclude_id: Optional[int]):
        query = self._group_query(media_item_id, language, part).filter(Subtitle.preferred.is_(True))
        if exclude_id is not None:
            query = query.filter(Subtitle.id != exclude_id)
        return query.first()

    def _place_in_group(self, row: Subtitle, old_group, was_preferred: bool) -> None:
        """字段已经改完后，决定这一份还是不是在用的。不提交。"""
        new_group = self._group_key(row)
        if was_preferred and old_group != new_group and old_group[0]:
            self._release(row)
        if not new_group[0]:
            row.preferred = False
            return
        if old_group == new_group:
            return
        other = self._preferred_other(new_group[0], new_group[1], new_group[2], row.id)
        row.preferred = other is None

    def _follow_group_change(self, row: Subtitle, old_group, was_preferred: bool) -> None:
        new_group = self._group_key(row)
        if was_preferred and old_group != new_group and old_group[0]:
            try:
                self._promote_if_single(old_group[0], old_group[1], old_group[2])
            except Exception:
                logger.exception("字幕换组后同步旧组失败: %s", old_group[0])
        if was_preferred and row.preferred:
            try:
                self._deliver_rows([row])
            except Exception:
                logger.exception("字幕换组后投递失败: %s", row.id)

    def _promote_if_single(self, media_item_id: Optional[int], language: str, part: int) -> None:
        if not media_item_id:
            return
        rows = self._group_query(media_item_id, language, part).all()
        if len(rows) != 1 or rows[0].preferred:
            return
        rows[0].preferred = True
        self.session.commit()
        self._deliver_rows([rows[0]])

    def _release(self, row: Subtitle) -> List[str]:
        """删掉这条记录记下的影片旁边的文件，并取消在用。不提交。"""
        kept = []
        details = []
        for path in load_delivered_paths(row.delivered_paths):
            deleted, gone = self._remove_delivered(path)
            if deleted:
                detail = f"已清理不再使用的字幕：{path}"
                details.append(detail)
            elif not gone:
                kept.append(path)
        row.delivered_paths = dump_delivered_paths(kept)
        row.preferred = False
        return details

    def _settle_paths(
        self,
        row: Subtitle,
        written: List[str],
        hold_dirs: set,
        limit_dirs: Optional[set] = None,
    ) -> List[str]:
        """这次写成功的路径记下来。只清理这次动过的目录里、已经不再使用的旧路径。"""
        previous = load_delivered_paths(row.delivered_paths)
        current = []
        seen = set()
        for path in written:
            norm = os.path.normpath(path)
            if norm in seen:
                continue
            seen.add(norm)
            current.append(norm)
        kept = list(current)
        details = []
        for old in previous:
            norm = os.path.normpath(old)
            if norm in seen:
                continue
            folder = os.path.dirname(norm)
            if limit_dirs is not None and folder not in limit_dirs:
                kept.append(norm)
                continue
            if folder in hold_dirs:
                kept.append(norm)
                continue
            deleted, gone = self._remove_delivered(norm)
            if deleted:
                details.append(f"已清理不再使用的字幕：{norm}")
            elif not gone:
                kept.append(norm)
        row.delivered_paths = dump_delivered_paths(kept)
        return details

    def _remove_delivered(self, path: str) -> Tuple[bool, bool]:
        """删除记下的字幕文件。返回 (已删除, 本来就不在)。"""
        if not path:
            return False, True
        extension = os.path.splitext(path)[1].lower()
        if extension not in subext_type:
            logger.info("拒绝删除非字幕路径：%s", path)
            return False, False
        try:
            root = os.path.abspath(settings.SUBTITLE_LOCATION)
            target = os.path.abspath(path)
            if os.path.commonpath([root, target]) == root:
                logger.info("拒绝删除字幕库内的文件：%s", path)
                return False, False
        except ValueError:
            return False, False
        if not os.path.lexists(path):
            return False, True
        try:
            if os.path.isdir(path):
                logger.info("拒绝删除目录：%s", path)
                return False, False
            os.remove(path)
            return True, False
        except OSError as exc:
            logger.info("清理字幕失败 %s: %s", path, exc)
            return False, False

    def _resolve_upload_item(
        self,
        filename: str,
        number: Optional[str],
        media_item_id: Optional[int],
    ) -> Optional[MediaItem]:
        """上传时决定挂到哪一条媒体项。指定的媒体项优先，否则用指定番号或文件名里的番号。"""
        if media_item_id:
            item = self.session.get(MediaItem, int(media_item_id))
            if not item or item.media_type not in _BINDABLE_TYPES:
                raise ValueError("请选择具体的电影、单集或番号")
            return item
        explicit = normalize_number(number)
        if explicit:
            return self._resolve_number_item(explicit)
        number_key = parse_number(filename)
        if number_key:
            return self._resolve_number_item(number_key)
        return None

    def _resolve_number_item(self, number: str) -> Optional[MediaItem]:
        """按番号找到媒体项。已有 metadata 而媒体项还不存在时才新建，并把同番号的转移记录挂上去。"""
        key = normalize_number(number)
        if not key:
            return None
        from bonita.modules.media_service.record_link import (
            ensure_number_media_item,
            find_number_media_item,
            link_records_with_number,
            metadata_for_number,
        )

        item = find_number_media_item(self.session, key)
        meta = metadata_for_number(self.session, key)
        if not meta:
            return item
        if not item:
            item = ensure_number_media_item(self.session, key, meta.title or key)
        if item:
            link_records_with_number(self.session, key, item)
        return item

    def _row_label(self, row: Subtitle) -> str:
        item = self.session.get(MediaItem, row.media_item_id) if row.media_item_id else None
        if item and item.number:
            return item.number
        if item and item.title:
            return item.title
        return row.original_name or str(row.id)

    def _records_for_items(self, item_ids: set):
        if not item_ids:
            return []
        rows = (
            self.session.query(TransRecords.destpath, TransRecords.media_item_id, TransRecords.part_number)
            .filter(
                TransRecords.media_item_id.in_(item_ids),
                TransRecords.success.is_(True),
                TransRecords.deleted.is_(False),
                TransRecords.destpath.isnot(None),
                TransRecords.destpath != "",
            )
            .all()
        )
        return [(destpath, media_item_id, part or 0) for destpath, media_item_id, part in rows]

    def _copy_to_video(self, row: Subtitle, video_path: str, overwrite: bool) -> Tuple[str, str, str]:
        label = f"{self._row_label(row)}#{row.id}"
        if not video_path or not os.path.isfile(video_path):
            detail = f"{label} 视频不存在：{video_path}"
            logger.info("字幕投递缺失：%s", detail)
            return "missing", detail, ""
        source = self._absolute(row.stored_path)
        if not source or not os.path.isfile(source):
            detail = f"{label} 字幕库文件不存在：{source}"
            logger.info("字幕投递缺失：%s", detail)
            return "missing", detail, ""
        extension = row.file_extension or os.path.splitext(source)[1]
        target = dest_subtitle_path(video_path, row.language, extension)
        identical = same_subtitle(source, target)
        newer = source_is_newer(source, target)
        if identical and not newer and not overwrite:
            detail = f"{label} 已跳过，目标与字幕库一致：{target}"
            logger.info("字幕投递跳过：%s（视频 %s）", detail, video_path)
            return "skipped", detail, target
        replaced = target_visible(target) or os.path.lexists(target)
        try:
            self._place_file(source, target)
        except OSError as exc:
            detail = f"{label} 写入失败 {target}：{exc}"
            logger.exception("字幕投递失败：%s（视频 %s，来源 %s）", detail, video_path, source)
            return "failed", detail, ""
        if replaced:
            reason = "字幕库文件较新" if identical and newer else "目标内容不同或不在目录中"
            detail = f"{label} 已覆盖 {target}（{reason}）"
            logger.info("字幕投递覆盖：%s（视频 %s，来源 %s）", detail, video_path, source)
            return "copied", detail, target
        logger.info("字幕投递复制：%s -> %s（视频 %s）", source, target, video_path)
        return "copied", "", target

    def _place_file(self, source: str, target: str) -> None:
        folder = os.path.dirname(target)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        temporary = f"{target}.{os.getpid()}.bonita-tmp"
        try:
            shutil.copyfile(source, temporary)
            os.chmod(temporary, _FILE_MODE)
            os.replace(temporary, target)
            os.chmod(target, _FILE_MODE)
        except Exception:
            if os.path.lexists(temporary):
                try:
                    os.remove(temporary)
                except OSError:
                    pass
            raise

    def _storage_relative(self, item: Optional[MediaItem], original_name: str, extension: str) -> str:
        filename = safe_filename(original_name, extension)
        number = normalize_number(item.number) if item and item.number else ""
        if item and number:
            return f"number/{safe_storage_key(number)}/{filename}"
        if item:
            return f"item/{item.id}/{filename}"
        return filename

    def _write(self, relative: str, content: bytes) -> str:
        path = self._absolute(relative)
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(path, "wb") as handle:
            handle.write(content)
        os.chmod(path, _FILE_MODE)
        return path

    def _move_stored(self, old_relative: str, new_relative: str) -> None:
        if not old_relative or old_relative == new_relative:
            return
        source = self._absolute(old_relative)
        target = self._absolute(new_relative)
        if not os.path.exists(source):
            raise ValueError("字幕文件已丢失")
        folder = os.path.dirname(target)
        if not os.path.exists(folder):
            os.makedirs(folder)
        if os.path.exists(target):
            os.remove(target)
        shutil.move(source, target)
        os.chmod(target, _FILE_MODE)
        self._prune(os.path.dirname(source))

    def _remove_file(self, relative: str, keep: str = "") -> None:
        if not relative or relative == keep:
            return
        path = self._absolute(relative)
        if path and os.path.isfile(path):
            os.remove(path)
            self._prune(os.path.dirname(path))

    def _absolute(self, relative: str) -> str:
        if not relative:
            return ""
        root = os.path.abspath(settings.SUBTITLE_LOCATION)
        os.makedirs(root, exist_ok=True)
        path = os.path.abspath(os.path.join(root, relative))
        if os.path.commonpath([root, path]) != root:
            raise ValueError("字幕路径无效")
        return path

    def _prune(self, directory: str) -> None:
        root = os.path.abspath(settings.SUBTITLE_LOCATION)
        current = os.path.abspath(directory)
        while current.startswith(root) and current != root:
            if not os.path.isdir(current) or os.listdir(current):
                break
            os.rmdir(current)
            current = os.path.dirname(current)
