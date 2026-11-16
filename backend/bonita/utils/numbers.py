from typing import Optional


def normalize_number(value: Optional[str]) -> str:
    """番号规范化：去首尾空白并大写。"""
    if not value:
        return ""
    return value.strip().upper()
