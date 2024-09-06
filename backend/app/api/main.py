from fastapi import APIRouter, Depends

from app.api.routes import login, users, tasks, settings
from app.api.deps import verify_token

api_router = APIRouter()
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"], dependencies=[Depends(verify_token)])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"], dependencies=[Depends(verify_token)])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"], dependencies=[Depends(verify_token)])
