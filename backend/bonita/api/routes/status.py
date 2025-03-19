from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    """
    健康检查端点，用于确认API服务运行状态
    """
    return {"status": "ok"}
