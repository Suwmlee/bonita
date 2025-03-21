from fastapi import APIRouter

from bonita import __version__, schemas

router = APIRouter()


@router.get("/health", response_model=schemas.StatusResponse)
def health_check():
    """
    健康检查端点，用于确认API服务运行状态
    """
    return schemas.StatusResponse(status="ok", version=__version__)
