from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from bonita.db.models.metadata import Metadata


class MetadataService:
    """元数据业务逻辑"""

    def __init__(self, session: Session):
        self.session = session

    def sync_crop_by_number(self, number: str, crop: bool) -> None:
        """将裁切标记同步到该番号对应的全部元数据。"""
        if not number:
            return
        self.session.query(Metadata).filter(
            func.upper(Metadata.number) == number.upper()
        ).update({Metadata.crop: crop}, synchronize_session="fetch")

    def get_crop_by_numbers(self, numbers: List[Optional[str]]) -> dict:
        """按番号（大写）返回最新一条元数据的 crop。没有本地元数据的番号不会出现在结果中。"""
        result = {}
        keys = [n.upper() for n in numbers if n]
        if not keys:
            return result
        rows = (
            self.session.query(Metadata)
            .filter(func.upper(Metadata.number).in_(keys))
            .order_by(Metadata.id.asc())
            .all()
        )
        for row in rows:
            if row.number:
                result[row.number.upper()] = row.crop
        return result

    def resolve_crop(self, number: Optional[str], crop_map: Optional[dict] = None) -> bool:
        """没有本地 metadata 时默认不裁切；有则用 metadata.crop。"""
        if not number:
            return False
        source = crop_map if crop_map is not None else self.get_crop_by_numbers([number])
        crop = source.get(number.upper())
        if crop is None:
            return False
        return bool(crop)

    def get_crop_by_number(self, number: Optional[str]) -> bool:
        return self.resolve_crop(number)
