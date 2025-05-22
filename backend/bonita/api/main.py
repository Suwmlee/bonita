from fastapi import APIRouter, Depends

from bonita.api.routes import login, mediaitem, records, resource, scraping_config, task_config, tasks, users, metadata, tools, settings, file_browser, status
from bonita.api.deps import verify_token
from bonita.api.websockets import logs as ws_logs

api_router = APIRouter()
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["user"], dependencies=[Depends(verify_token)])
api_router.include_router(tasks.router, prefix="/tasks", tags=["task"], dependencies=[Depends(verify_token)])
api_router.include_router(task_config.router, prefix="/tasks/config",
                          tags=["taskConfig"], dependencies=[Depends(verify_token)])
api_router.include_router(scraping_config.router, prefix="/scraping/config",
                          tags=["scrapingConfig"], dependencies=[Depends(verify_token)])
api_router.include_router(records.router, prefix="/records",
                          tags=["record"], dependencies=[Depends(verify_token)])
api_router.include_router(metadata.router, prefix="/metadata",
                          tags=["metadata"], dependencies=[Depends(verify_token)])
api_router.include_router(mediaitem.router, prefix="/mediaitems",
                          tags=["mediaitem"], dependencies=[Depends(verify_token)])
api_router.include_router(tools.router, prefix="/tools",
                          tags=["tools"], dependencies=[Depends(verify_token)])
api_router.include_router(settings.router, prefix="/settings",
                          tags=["settings"], dependencies=[Depends(verify_token)])
api_router.include_router(resource.router, prefix="/resource",
                          tags=["resource"])
api_router.include_router(file_browser.router, prefix="/files",
                          tags=["files"], dependencies=[Depends(verify_token)])
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(ws_logs.router, prefix="/ws", tags=["websocket"])
