from typing import List, Optional
from pydantic import BaseModel, model_validator
from datetime import date


class MetadataBase(BaseModel):
    number: str
    title: str
    studio: Optional[str] = None
    release: Optional[date] = None
    year: Optional[int] = None
    runtime: Optional[str] = None
    genre: Optional[str] = None
    rating: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    outline: Optional[str] = None
    director: Optional[str] = None
    actor: Optional[str] = None
    actor_photo: Optional[str] = None
    cover: Optional[str] = None
    cover_small: Optional[str] = None
    extrafanart: Optional[str] = None
    trailer: Optional[str] = None
    tag: Optional[str] = None
    label: Optional[str] = None
    series: Optional[str] = None
    userrating: Optional[float] = None
    uservotes: Optional[int] = None
    detailurl: Optional[str] = None
    site: Optional[str] = None

    @model_validator(mode='before')
    def process_fields(cls, values):
        if 'source' in values:
            values['site'] = values['source']
        if 'website' in values:
            values['detailurl'] = values['website']

        for field, value in values.items():
            if value is None:
                continue

            if isinstance(value, dict):
                values[field] = str(value)
            elif isinstance(value, list):
                values[field] = ', '.join(map(str, value))
            else:
                values[field] = value

        return values


class MetadataMixed(MetadataBase):
    """ 额外自定义信息，不止元数据内容
    """
    extra_filename: Optional[str] = None
    extra_folder: Optional[str] = None
    extra_part: Optional[int] = None

    class Config:
        from_attributes = True


class MetadataPublic(MetadataBase):
    id: int

    class Config:
        from_attributes = True


class MetadataCollection(BaseModel):
    data: List[MetadataPublic]
    count: int
