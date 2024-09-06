
import logging
import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bonita"
    API_V1_STR: str = "/api/v1"
    # 要与 alembic.ini 同步
    ALEMBIC_LOCATION: str = "./app/alembic"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./data/db.sqlite3"
    # 日志
    LOGGING_FORMAT: str = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    LOGGING_LOCATION: str = "./data/bonita.log"
    LOGGING_LEVEL: int = logging.INFO
    # SECRET_KEY: str = secrets.token_urlsafe(32)
    SECRET_KEY: str = "secret key"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # 跨域
    BACKEND_CORS_ORIGINS: list = ["*"]
    # 初始化管理员
    FIRST_SUPERUSER: str = "admin"
    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "change"
    # 是否开放注册
    USERS_OPEN_REGISTRATION: bool = False


settings = Settings()
