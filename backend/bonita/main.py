
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from bonita.core.config import settings
from bonita.core.db import init_db, init_super_user, upgrade_db
from bonita.core.task import init_watcher
from bonita.api.main import api_router

# celery client
from bonita.worker import celery


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


def create_app() -> FastAPI:
    current_app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        generate_unique_id_function=custom_generate_unique_id
    )

    # Set all CORS enabled origins
    current_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # initial router
    current_app.include_router(api_router, prefix=settings.API_V1_STR)
    return current_app


def log_config():
    """
    日志配置
    """
    max_log_size = 5 * 1024 * 1024  # 5 MB
    backup_count = 5
    formatter = logging.Formatter(settings.LOGGING_FORMAT)
    handler = RotatingFileHandler(settings.LOGGING_LOCATION, maxBytes=max_log_size, backupCount=backup_count)
    handler.setFormatter(formatter)
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        handlers=[handler]
    )


app = create_app()
app.celery_app = celery


log_config()
init_db()
init_super_user()
upgrade_db()
init_watcher()
