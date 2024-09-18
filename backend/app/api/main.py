from fastapi import APIRouter, Depends

from app.api.routes import login, scraping_setting, task_transfer, users, task
from app.api.deps import verify_token

api_router = APIRouter()
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["user"], dependencies=[Depends(verify_token)])
api_router.include_router(task.router, prefix="/task", tags=["task"], dependencies=[Depends(verify_token)])
api_router.include_router(task_transfer.router, prefix="/tasks/transfer",
                          tags=["transferTask"], dependencies=[Depends(verify_token)])
api_router.include_router(scraping_setting.router, prefix="/scraping/settings",
                          tags=["scrapingSetting"], dependencies=[Depends(verify_token)])
