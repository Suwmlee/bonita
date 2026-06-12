import logging
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from bonita import __version__
from bonita.core.config import settings
from bonita.core.db import init_db
from bonita.core.service import init_service
from bonita.api.main import api_router
from bonita.utils.logger import init_log_config

# celery client
from bonita.worker import celery


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


def create_app() -> FastAPI:
    current_app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        generate_unique_id_function=custom_generate_unique_id,
        version=__version__,
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


app = create_app()
app.celery_app = celery


init_log_config()
logger = logging.getLogger(__name__)
logger.info(f"Bonita version: {__version__}")
init_db()
init_service()
