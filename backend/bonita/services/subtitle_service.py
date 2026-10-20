import logging
import os
import re
import shutil
import stat
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from bonita.core.config import settings
from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.record import TransRecords
from bonita.db.models.subtitle import Subtitle
from bonita.modules.scraping.number_parser import FileNumInfo, rules_parser
from bonita.utils.filehelper import subext_type

logger = logging.getLogger(__name__)

IDENTITY_NUMBER = "number"
DEFAULT_LANGUAGE = "zh-Hans"

_LANG_RULES = (
    (re.compile(r"(?:^|[.\-_])(?:zh[-_]?hant|zht|cht|zh[-_]?tw)(?=$|[.\-_])", re.I), "zh-Hant"),
    (re.compile(r"(?:^|[.\-_])(?:zh[-_]?hans|zhs|chs|zh[-_]?cn|chi|chn)(?=$|[.\-_])", re.I), "zh-Hans"),
    (re.compile(r"(?:^|[.\-_])(?:jpn|jp|ja)(?=$|[.\-_])", re.I), "ja"),
    (re.compile(r"(?:^|[.\-_])(?:eng|en)(?=$|[.\-_])", re.I), "en"),
    (re.compile(r"(?:^|[.\-_])(?:tc)(?=$|[.\-_])", re.I), "zh-Hant"),
    (re.compile(r"(?:^|[.\-_])(?:sc|zh|cn|c)(?=$|[.\-_])", re.I), "zh-Hans"),
)

_DELIVER_SUFFIX = {
    "zh-Hans": ".chs",
    "zh-Hant": ".cht",
    "ja": ".ja",
    "en": ".en",
}

_FILE_MODE = stat.S_IRWXU | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH


def normalize_number(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip().upper()


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
    return _DELIVER_SUFFIX.get(language or "", f".{language}" if language else ".chs")


def dest_subtitle_path(video_path: str, language: str, extension: str) -> str:
    folder = os.path.dirname(video_path)
    stem = os.path.splitext(os.path.basename(video_path))[0]
    ext = extension if str(extension).startswith(".") else f".{extension}"
    return os.path.join(folder, f"{stem}{deliver_suffix(language)}{ext}")


def safe_storage_key(number: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (number or "").strip())
    cleaned = cleaned.strip("._")
    return cleaned or "unknown"


class SubtitleService:
    def __init__(self, session: Session):
        self.session = session

    def list_subtitles(
        self,
        skip: int = 0,
        limit: int = 50,
        filter_text: Optional[str] = None,
        number: Optional[str] = None,
        unmatched: bool = False,
    ) -> Tuple[List[Subtitle], int]:
        query = self.session.query(Subtitle).filter(Subtitle.identity_type == IDENTITY_NUMBER)
        if unmatched:
            query = query.filter(or_(Subtitle.identity_key.is_(None), Subtitle.identity_key == ""))
        elif number:
            query = query.filter(func.upper(Subtitle.identity_key) == normalize_number(number))
        if filter_text:
            like = f"%{filter_text.strip()}%"
            query = query.filter(or_(
                Subtitle.identity_key.like(like),
                Subtitle.original_name.like(like),
            ))
        count = query.count()
        rows = query.order_by(Subtitle.updatetime.desc(), Subtitle.id.desc()).offset(skip).limit(limit).all()
        return rows, count

    def get(self, subtitle_id: int) -> Optional[Subtitle]:
        return self.session.get(Subtitle, subtitle_id)

    def counts_for(self, pairs: List[Tuple[str, int]]) -> dict:
        keys = {normalize_number(number) for number, _part in pairs if number}
        keys.discard("")
        if not keys:
            return {}
        rows = (
            self.session.query(Subtitle.identity_key, Subtitle.part_number, func.count(Subtitle.id))
            .filter(
                Subtitle.identity_type == IDENTITY_NUMBER,
                func.upper(Subtitle.identity_key).in_(keys),
            )
            .group_by(Subtitle.identity_key, Subtitle.part_number)
            .all()
        )
        return {(normalize_number(key), part or 0): count for key, part, count in rows}

    def save_bytes(self, filename: str, content: bytes, number: Optional[str] = None) -> dict:
        original_name = os.path.basename(filename or "").strip()
        if not original_name:
            raise ValueError("缺少文件名")
        extension = os.path.splitext(original_name)[1].lower()
        if extension not in subext_type:
            raise ValueError(f"不支持的字幕格式: {original_name}")
        if not content:
            raise ValueError(f"文件为空: {original_name}")

        explicit = normalize_number(number)
        identity_key = explicit or parse_number(original_name)
        language = parse_language(original_name)
        part_number = parse_part(original_name)
        now = datetime.now()

        existing = None
        if identity_key:
            existing = (
                self.session.query(Subtitle)
                .filter(
                    Subtitle.identity_type == IDENTITY_NUMBER,
                    func.upper(Subtitle.identity_key) == identity_key,
                    Subtitle.language == language,
                    Subtitle.part_number == part_number,
                    Subtitle.file_extension == extension,
                )
                .first()
            )

        if existing:
            relative = self._storage_relative(identity_key, language, part_number, extension)
            self._write(relative, content)
            self._remove_file(existing.stored_path, keep=relative)
            existing.original_name = original_name
            existing.stored_path = relative
            existing.updatetime = now
            self.session.commit()
            return {"subtitle": existing, "replaced": True, "unmatched": False}

        relative = self._storage_relative(identity_key, language, part_number, extension)
        self._write(relative, content)
        row = Subtitle(
            identity_type=IDENTITY_NUMBER,
            identity_key=identity_key,
            language=language,
            part_number=part_number,
            original_name=original_name,
            stored_path=relative,
            file_extension=extension,
            createtime=now,
            updatetime=now,
        )
        row.create(self.session)
        return {"subtitle": row, "replaced": False, "unmatched": not bool(identity_key)}

    def update_subtitle(self, subtitle_id: int, identity_key: str, language: str, part_number: int) -> Optional[Subtitle]:
        row = self.get(subtitle_id)
        if not row:
            return None
        key = normalize_number(identity_key)
        language = (language or DEFAULT_LANGUAGE).strip() or DEFAULT_LANGUAGE
        part_number = int(part_number or 0)
        extension = row.file_extension or os.path.splitext(row.original_name or "")[1].lower()

        if key:
            conflict = (
                self.session.query(Subtitle)
                .filter(
                    Subtitle.id != row.id,
                    Subtitle.identity_type == IDENTITY_NUMBER,
                    func.upper(Subtitle.identity_key) == key,
                    Subtitle.language == language,
                    Subtitle.part_number == part_number,
                    Subtitle.file_extension == extension,
                )
                .first()
            )
            if conflict:
                raise ValueError("已有相同番号、语言、部次和格式的字幕")

        relative = self._storage_relative(key, language, part_number, extension)
        self._move_stored(row.stored_path, relative)
        row.identity_type = IDENTITY_NUMBER
        row.identity_key = key
        row.language = language
        row.part_number = part_number
        row.file_extension = extension
        row.stored_path = relative
        row.updatetime = datetime.now()
        self.session.commit()
        return row

    def delete_subtitle(self, subtitle_id: int) -> bool:
        row = self.get(subtitle_id)
        if not row:
            return False
        self._remove_file(row.stored_path)
        self.session.delete(row)
        self.session.commit()
        return True

    def deliver_subtitle(self, subtitle_id: int, overwrite: bool = False):
        row = self.get(subtitle_id)
        if not row:
            return None
        if not normalize_number(row.identity_key):
            raise ValueError("字幕尚未关联番号")
        return self._deliver_rows([row], overwrite=overwrite)

    def deliver_number(self, number: str, part_number: Optional[int] = None, overwrite: bool = False) -> dict:
        key = normalize_number(number)
        if not key:
            raise ValueError("缺少番号")
        query = self.session.query(Subtitle).filter(
            Subtitle.identity_type == IDENTITY_NUMBER,
            func.upper(Subtitle.identity_key) == key,
        )
        if part_number is not None:
            query = query.filter(Subtitle.part_number == part_number)
        return self._deliver_rows(query.all(), overwrite=overwrite)

    def deliver_for_transfer(self, srcpath: str, destpath: str, part_number: int = 0, number: Optional[str] = None) -> int:
        """转移完成后，把字幕库里匹配的字幕复制到这次的目标文件旁边。"""
        if not destpath:
            return 0
        key = normalize_number(number)
        if not key and srcpath:
            extra = self.session.query(ExtraInfo).filter(ExtraInfo.filepath == srcpath).first()
            if extra and extra.number:
                key = normalize_number(extra.number)
        if not key and srcpath:
            key = parse_number(srcpath)
        if not key:
            return 0
        part = int(part_number or 0)
        rows = (
            self.session.query(Subtitle)
            .filter(
                Subtitle.identity_type == IDENTITY_NUMBER,
                func.upper(Subtitle.identity_key) == key,
                Subtitle.part_number == part,
            )
            .all()
        )
        return sum(
            self._copy_to_video(row, destpath, overwrite=False) == "copied"
            for row in rows
        )

    def _deliver_rows(self, rows: List[Subtitle], overwrite: bool = False) -> dict:
        result = {"copied": 0, "skipped": 0, "missing": 0}
        if not rows:
            return result
        keys = {normalize_number(row.identity_key) for row in rows if row.identity_key}
        records = self._records_for_numbers(keys)
        seen = set()
        for row in rows:
            key = normalize_number(row.identity_key)
            targets = [
                destpath
                for destpath, number, part in records
                if normalize_number(number) == key and int(part or 0) == int(row.part_number or 0)
            ]
            if not targets:
                result["missing"] += 1
                continue
            for destpath in targets:
                marker = (row.id, os.path.normpath(destpath))
                if marker in seen:
                    continue
                seen.add(marker)
                result[self._copy_to_video(row, destpath, overwrite=overwrite)] += 1
        return result

    def _records_for_numbers(self, keys: set):
        if not keys:
            return []
        rows = (
            self.session.query(TransRecords.destpath, ExtraInfo.number, TransRecords.part_number)
            .join(ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath)
            .filter(
                func.upper(ExtraInfo.number).in_(keys),
                TransRecords.success.is_(True),
                TransRecords.deleted.is_(False),
                TransRecords.destpath.isnot(None),
                TransRecords.destpath != "",
            )
            .all()
        )
        return [(destpath, number, part or 0) for destpath, number, part in rows]

    def _copy_to_video(self, row: Subtitle, video_path: str, overwrite: bool) -> str:
        if not video_path or not os.path.exists(video_path):
            return "missing"
        source = self._absolute(row.stored_path)
        if not source or not os.path.exists(source):
            return "missing"
        extension = row.file_extension or os.path.splitext(source)[1]
        target = dest_subtitle_path(video_path, row.language, extension)
        if os.path.exists(target) and not overwrite:
            return "skipped"
        folder = os.path.dirname(target)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
        shutil.copyfile(source, target)
        os.chmod(target, _FILE_MODE)
        return "copied"

    def _storage_relative(self, identity_key: str, language: str, part_number: int, extension: str) -> str:
        if not identity_key:
            return f"inbox/{uuid.uuid4().hex}{extension}"
        part = f"-EP{int(part_number):02d}" if part_number else ""
        return f"number/{safe_storage_key(identity_key)}/{language}{part}{extension}"

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
