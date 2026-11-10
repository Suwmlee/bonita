import ast
import json
import re
from typing import List, Optional

UNKNOWN_ACTOR = "佚名"
_ACTOR_SPLIT = re.compile(r"[,，、|/]+")


def split_actor_names(actor: Optional[str]) -> List[str]:
    """演员字段按逗号等分隔。空值归到佚名，同一条里的重复名字只留一次。"""
    text = (actor or "").strip()
    if not text:
        return [UNKNOWN_ACTOR]
    names: List[str] = []
    seen = set()
    for part in _ACTOR_SPLIT.split(text):
        name = part.strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names or [UNKNOWN_ACTOR]


def parse_actor_photos(raw: Optional[str]) -> dict:
    """actor_photo 可能是 JSON，也可能是 Python 字典字符串。"""
    text = (raw or "").strip()
    if not text:
        return {}
    value = None
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        try:
            value = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return {}
    if not isinstance(value, dict):
        return {}
    photos = {}
    for key, photo in value.items():
        name = str(key).strip()
        url = str(photo).strip() if photo is not None else ""
        if name and url:
            photos[name] = url
    return photos
