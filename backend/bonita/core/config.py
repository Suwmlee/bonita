import logging
import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bonita"
    API_V1_STR: str = "/api/v1"
    # 与 alembic.ini 同步
    ALEMBIC_LOCATION: str = "./bonita/alembic"
    # DATABASE_LOCATION
    DATABASE_LOCATION: str = "./data/db.sqlite3"
    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{DATABASE_LOCATION}"
    # CACHE_LOCATION
    CACHE_LOCATION: str = "./data/cache"
    # CELERY
    # CELERY_BROKER_URL: str = f"sqla+sqlite:///{DATABASE_LOCATION}"
    # CELERY_RESULT_BACKEND: str = f"db+sqlite:///{DATABASE_LOCATION}"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    # 最大并发任务数, 受 worker 数量影响
    MAX_CONCURRENT_TASKS: int = 5
    # 日志
    LOGGING_FORMAT: str = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    LOGGING_LOCATION: str = "./data/bonita.log"
    LOGGING_LEVEL: int = logging.DEBUG
    # SECRET_KEY: str = secrets.token_urlsafe(32)
    SECRET_KEY: str = "secret key"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # 跨域
    BACKEND_CORS_ORIGINS: list = ["*"]
    # 初始化管理员
    FIRST_SUPERUSER: str = "admin"
    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changepwd"
    # 是否开放注册
    USERS_OPEN_REGISTRATION: bool = False


settings = Settings()
