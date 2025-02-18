
from typing import Generator
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session, declared_attr, as_declarative

from bonita.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI,
                       connect_args={"check_same_thread": False})

SessionFactory = sessionmaker(bind=engine)


def get_db() -> Generator:
    """
    获取数据库会话, 用于WEB请求
    :return: Session
    """
    db = None
    try:
        db = SessionFactory()
        yield db
    finally:
        if db:
            db.close()


@as_declarative()
class Base:
    __name__: str

    def create(self, session: Session):
        session.add(self)
        session.commit()

    @declared_attr
    def __tablename__(self) -> str:
        return self.__name__.lower()

    def update(self, session: Session, payload: dict):
        payload = {k: v for k, v in payload.items() if v is not None}
        for key, value in payload.items():
            setattr(self, key, value)
        if inspect(self).detached:
            session.add(self)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}

    def filter_dict(self, source_dict):
        valid_columns = {column.name for column in self.__table__.columns}
        filtered_dict = {key: value for key, value in source_dict.items() if key in valid_columns}
        return filtered_dict
