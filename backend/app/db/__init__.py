
from app.core.config import settings
from app.core.db import Base, engine, SessionFactory
from app.db.models import *
from app.core.security import get_password_hash


def init_db():
    """
    初始化数据库
    """
    Base.metadata.create_all(bind=engine)


def init_super_user():
    """
    初始化超级管理员
    """
    with SessionFactory() as session:
        _user = User.get_user_by_email(session=session, email=settings.FIRST_SUPERUSER_EMAIL)
        if not _user:
            _user = User(
                name=settings.FIRST_SUPERUSER,
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_active=True,
                is_superuser=True
            )
            _user.create(session)
