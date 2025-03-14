
import logging
from alembic.command import upgrade, stamp
from alembic.config import Config

from bonita.core.config import settings
from bonita.core.security import get_password_hash
from bonita.db import Base, engine, SessionFactory
from bonita.db.models import *

logger = logging.getLogger(__name__)

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


def upgrade_db():
    """
    更新数据库
    """
    try:
        alembic_cfg = Config()
        alembic_cfg.set_main_option('script_location', settings.ALEMBIC_LOCATION)
        alembic_cfg.set_main_option('sqlalchemy.url', settings.SQLALCHEMY_DATABASE_URI)
        upgrade(alembic_cfg, 'head')
    except Exception as e:
        logger.error(f"升级数据库失败: {e}")
