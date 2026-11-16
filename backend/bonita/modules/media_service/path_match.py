"""远端路径与本地转移记录匹配。"""

import os

from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.record import TransRecords
from bonita.modules.media_service.client import ITEM_MOVIE, ITEM_VIDEO, RemoteItem
from bonita.modules.media_service.record_link import media_item_for_numbered_record
from bonita.modules.media_service.sync_context import current_sync


def paths_match(remote_path: str, destpath: str) -> bool:
    left = (remote_path or "").replace("\\", "/").rstrip("/").lower()
    right = (destpath or "").replace("\\", "/").rstrip("/").lower()
    if not left or not right:
        return False
    if left == right:
        return True
    return left.endswith(right) or right.endswith(left)


def remote_file_paths(item: RemoteItem) -> list:
    paths = []
    seen = set()
    candidates = []
    if item.path:
        candidates.append(item.path)
    candidates.extend(item.source_paths or [])
    for path in candidates:
        key = (path or "").replace("\\", "/").rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def normalize_path(path: str) -> str:
    return (path or "").replace("\\", "/").rstrip("/").lower()


def best_path_match(path: str, candidates):
    """candidates: iterable of (path, payload)。全等优先、更长路径优先，返回 payload。"""
    if not path:
        return None
    norm = normalize_path(path)
    matches = [(p, payload) for p, payload in candidates if p and paths_match(path, p)]
    if not matches:
        return None
    matches.sort(
        key=lambda row: (normalize_path(row[0]) == norm, len(row[0] or "")),
        reverse=True,
    )
    return matches[0][1]


def _like_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_transfer_record(session, filepath):
    if not filepath:
        return None, None
    ctx = current_sync()
    if ctx is not None and filepath in ctx.exact_records:
        return ctx.exact_records[filepath]
    result = session.query(TransRecords, ExtraInfo).outerjoin(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
    ).filter(TransRecords.destpath == filepath).first()
    pair = (result[0], result[1]) if result else (None, None)
    if ctx is not None:
        ctx.exact_records[filepath] = pair
    return pair


def find_record_for_path(session, remote_path: str):
    """一条远端路径对到一条记录。先全等，再按后缀比较。"""
    if not remote_path:
        return None
    ctx = current_sync()
    if ctx is not None and remote_path in ctx.path_records:
        return ctx.path_records[remote_path]
    record, _extra = find_transfer_record(session, remote_path)
    if record:
        if ctx is not None:
            ctx.path_records[remote_path] = record
        return record
    basename = os.path.basename(remote_path.replace("\\", "/").rstrip("/"))
    if not basename:
        if ctx is not None:
            ctx.path_records[remote_path] = None
        return None
    rows = (
        session.query(TransRecords)
        .filter(TransRecords.destpath.ilike(f"%{_like_escape(basename)}", escape="\\"))
        .all()
    )
    matches = [row for row in rows if paths_match(remote_path, row.destpath or "")]
    found = best_path_match(remote_path, ((row.destpath or "", row) for row in matches))
    if ctx is not None:
        ctx.path_records[remote_path] = found
    return found


def dest_paths_for_media_item(session, media_item) -> list:
    if not media_item or not (media_item.number or "").strip():
        return []
    number = media_item.number.strip()
    ctx = current_sync()
    if ctx is not None and ctx.dest_paths_by_number is not None:
        return list(ctx.dest_paths_by_number.get(number) or [])
    rows = session.query(TransRecords.destpath).join(
        ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath
    ).filter(ExtraInfo.number == number).all()
    return list(dict.fromkeys(path for (path,) in rows if path))


def number_item_for_remote(session, item: RemoteItem):
    if item.item_type not in (ITEM_MOVIE, ITEM_VIDEO):
        return None
    for path in remote_file_paths(item):
        record = find_record_for_path(session, path)
        if not record:
            continue
        number_item = media_item_for_numbered_record(session, record, create=True)
        if number_item:
            return number_item
    return None
