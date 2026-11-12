"""ASSETS 路径约定：库内存相对路径，读盘拼绝对路径。

可写目标：
- covers/<番号>/、actors/<名>/（正式归档）
- cache/（无 hint 时的临时预览区；提交/带 hint 后再搬迁归档）
禁止新写入裸 covers/、actors/。
"""

from __future__ import annotations

import os
import re
from typing import Optional

from bonita.core.config import settings

COVER_FOLDER = "covers"
ACTOR_PHOTO_FOLDER = "actors"
CACHE_FOLDER = "cache"
LOCAL_KEY_PREFIX = "local:"
_MD5_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


class AssetsFolderError(ValueError):
    """目标不是明确归档目录（covers/<番号> 或 actors/<名>）。"""


def assets_root() -> str:
    return os.path.abspath(settings.ASSETS_LOCATION)


def normalize_rel(path: str) -> str:
    return (path or "").replace("\\", "/").strip("/")


def is_specific_assets_folder(folder: Optional[str]) -> bool:
    """covers/<番号>、actors/<名> 为明确子目录；裸 covers/actors/cache 不算。"""
    parts = [p for p in normalize_rel(folder or "").split("/") if p]
    return len(parts) >= 2


def require_specific_assets_folder(folder: Optional[str]) -> str:
    """仅允许明确归档目录（搬迁目标用）。"""
    text = normalize_rel(folder or "")
    if not is_specific_assets_folder(text):
        raise AssetsFolderError("invalid folder")
    return text


def resolve_write_folder(folder: Optional[str]) -> str:
    """落盘目标：明确子目录原样；否则落到 cache/。"""
    text = normalize_rel(folder or "")
    if is_specific_assets_folder(text):
        return text
    return CACHE_FOLDER


def assets_folder_abs(folder: str) -> str:
    return os.path.abspath(os.path.join(assets_root(), normalize_rel(folder)))


def to_stored_path(filepath: str) -> str:
    """写入 ImageCache.filepath：优先存相对 ASSETS 的路径（/ 分隔）。"""
    text = (filepath or "").strip()
    if not text:
        return ""
    root = assets_root()
    abs_fp = os.path.abspath(text) if os.path.isabs(text) else os.path.abspath(
        os.path.join(root, text)
    )
    try:
        if os.path.commonpath([abs_fp, root]) == root:
            return normalize_rel(os.path.relpath(abs_fp, root))
    except ValueError:
        pass
    if not os.path.isabs(text):
        return normalize_rel(text)
    return abs_fp


def to_abs_path(stored: Optional[str]) -> str:
    """读 ImageCache.filepath：相对路径拼 ASSETS；兼容历史绝对路径。"""
    text = (stored or "").strip()
    if not text:
        return ""
    if os.path.isabs(text):
        return os.path.abspath(text)
    return os.path.abspath(os.path.join(assets_root(), text))


def path_under_folder(filepath: str, folder: str) -> bool:
    if not filepath or not folder:
        return False
    target = assets_folder_abs(folder)
    try:
        return os.path.commonpath([os.path.abspath(filepath), target]) == target
    except ValueError:
        return False


def local_image_key(content_md5: str) -> str:
    """本地上传逻辑键。"""
    digest = (content_md5 or "").strip().lower()
    return f"{LOCAL_KEY_PREFIX}{digest}"


def content_hash_from_key(key: Optional[str]) -> str:
    """从 local:<md5> 或历史裸 md5 键取出内容哈希；否则空串。"""
    text = (key or "").strip()
    if not text or text.startswith(("http://", "https://")):
        return ""
    if text.lower().startswith(LOCAL_KEY_PREFIX):
        digest = text[len(LOCAL_KEY_PREFIX) :].strip()
        return digest.lower() if _MD5_RE.match(digest) else ""
    if _MD5_RE.match(text):
        return text.lower()
    return ""


def is_remote_image_key(key: Optional[str]) -> bool:
    text = (key or "").strip()
    return text.startswith(("http://", "https://"))
