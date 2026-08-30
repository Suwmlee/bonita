import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Request

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.services.watch_sync_service import WatchSyncService

router = APIRouter()
logger = logging.getLogger(__name__)


async def _parse_emby_payload(request: Request) -> Optional[dict[str, Any]]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        return payload if isinstance(payload, dict) else None

    form = await request.form()
    raw = form.get("data") or form.get("payload")
    if raw is None:
        body = await request.body()
        if not body:
            return None
        payload = json.loads(body)
        return payload if isinstance(payload, dict) else None
    if hasattr(raw, "read"):
        raw = (await raw.read()).decode("utf-8")
    payload = json.loads(str(raw))
    return payload if isinstance(payload, dict) else None


@router.post("/emby", response_model=schemas.Response)
async def emby_webhook(request: Request, session: SessionDep):
    """接收 Emby Webhooks 插件推送的播放、观看/收藏状态和新媒体入库事件。"""
    try:
        payload = await _parse_emby_payload(request)
    except Exception as e:
        logger.error(f"解析 Emby Webhook 失败: {e}")
        return schemas.Response(success=False, message="invalid webhook payload")

    if not payload:
        return schemas.Response(success=False, message="empty webhook payload")

    try:
        result = WatchSyncService(session).handle_webhook(payload)
        return schemas.Response(
            success=True,
            message=f"emby webhook {result}",
            data={"result": result, "event": payload.get("Event") or payload.get("event")},
        )
    except Exception as e:
        logger.error(f"处理 Emby Webhook 失败: {e}")
        return schemas.Response(success=False, message=str(e))
