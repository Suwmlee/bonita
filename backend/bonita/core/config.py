
import os
import logging
import secrets
import yaml
from typing import Any, Dict, Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    自定义 YAML 配置源：
    - 通过环境变量 `BONITA_CONFIG` 指定 YAML 文件路径；否则使用默认路径 `./data/config.yaml`
    - 若文件不存在或为空，则返回空配置
    """

    def __init__(self, settings_cls: type[BaseSettings], yaml_file_path: str) -> None:
        super().__init__(settings_cls)
        self.yaml_file_path = yaml_file_path

    def __call__(self) -> Dict[str, Any]:  # type: ignore[override]
        yaml_path = self.yaml_file_path
        if not yaml_path or not os.path.exists(yaml_path):
            return {}
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                return {}
            # 仅返回一层平铺键，和 Settings 字段名一致即可
            return {str(k): v for k, v in data.items()}
        except Exception:
            # 读取失败时不阻断启动，交由其他配置源接管
            return {}

    # 为兼容 pydantic-settings 抽象基类要求，提供占位实现。
    # 实际不会被调用，因为我们覆写了 __call__ 并返回完整字典。
    def get_field_value(self, *args, **kwargs):  # type: ignore[override]
        return None, None, False


class Settings(BaseSettings):
    # 默认不区分大小写；支持在容器/服务器上通过环境变量覆盖
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )
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
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", f"sqla+sqlite:///{DATABASE_LOCATION}")
    CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", f"db+sqlite:///{DATABASE_LOCATION}")
    # 最大并发任务数, 受 worker 数量影响
    MAX_CONCURRENT_TASKS: int = os.environ.get("MAX_CONCURRENT_TASKS", 5)
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
    FIRST_SUPERUSER_PASSWORD: str = "changepwd"
    # 是否开放注册
    USERS_OPEN_REGISTRATION: bool = False

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        配置读取优先级（前者优先级更高）：
        1) 初始化传入的值（init）
        2) YAML 文件（通过 `BONITA_CONFIG` 指定，默认 `./data/config.yaml`）
        3) 环境变量（env）
        """
        yaml_path = os.environ.get("BONITA_CONFIG", "./data/config.yaml")
        yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_path)
        return (
            init_settings,
            yaml_settings,
            env_settings,
        )


settings = Settings()
