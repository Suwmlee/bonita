from fastapi import APIRouter, Depends

from bonita.api.routes import login, records, scraping_setting, task_transfer, users, task, metadata
from bonita.api.deps import verify_token

api_router = APIRouter()
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["user"], dependencies=[Depends(verify_token)])
api_router.include_router(task.router, prefix="/task", tags=["task"], dependencies=[Depends(verify_token)])
api_router.include_router(task_transfer.router, prefix="/tasks/transfer",
                          tags=["transferTask"], dependencies=[Depends(verify_token)])
api_router.include_router(scraping_setting.router, prefix="/scraping/settings",
                          tags=["scrapingSetting"], dependencies=[Depends(verify_token)])
api_router.include_router(records.router, prefix="/records",
                          tags=["transRecords"], dependencies=[Depends(verify_token)])
api_router.include_router(metadata.router, prefix="/metadata",
                          tags=["metadata"], dependencies=[Depends(verify_token)])
