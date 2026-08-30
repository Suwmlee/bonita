import os
import re
import asyncio
import logging
from collections import deque
from typing import List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.websockets import WebSocketState
from jose import jwt, JWTError
from pydantic import ValidationError
from starlette.requests import ClientDisconnect

from bonita import schemas
from bonita.core.config import settings
from bonita.core import security
from bonita.utils.logger import list_log_files

router = APIRouter()
logger = logging.getLogger(__name__)

_WS_GONE = (WebSocketDisconnect, ClientDisconnect, RuntimeError)

LOG_PATTERN = re.compile(r"\[(.*?)\] (\w+) in ([\w\.]+): (.*)")
HISTORY_LINE_LIMIT = 1000
ALLOWED_LEVELS = {"debug", "info", "warning", "error", "critical"}


async def verify_ws_token(websocket: WebSocket, token: str = Query(...)) -> schemas.TokenPayload:
    """
    验证WebSocket连接的令牌
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return schemas.TokenPayload(**payload)
    except (JWTError, ValidationError):
        await _reject_websocket(websocket)
        return None


async def _reject_websocket(websocket: WebSocket) -> None:
    if websocket.client_state == WebSocketState.CONNECTING:
        await websocket.accept()
    if websocket.client_state == WebSocketState.CONNECTED:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)


def parse_log_line(line: str) -> Optional[schemas.LogEntry]:
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None
    timestamp, log_level, log_module, message = match.groups()
    return schemas.LogEntry(
        timestamp=timestamp,
        level=log_level,
        module=log_module,
        message=message,
    )


def normalize_level(level: Optional[str]) -> Optional[str]:
    if not level:
        return None
    value = level.strip().lower()
    if value == "warn":
        value = "warning"
    if value not in ALLOWED_LEVELS:
        return None
    return value


def read_recent_logs(
    log_file_path: str,
    limit: int = HISTORY_LINE_LIMIT,
    level: Optional[str] = None,
) -> List[schemas.LogEntry]:
    """
    从当前日志和轮转备份中取最近 limit 条已解析日志。
    指定 level 时，从文件中凑满该级别的 limit 条，而不是先截最近 1000 行再筛选。
    """
    level_norm = normalize_level(level)
    files = list_log_files(log_file_path)
    if not files:
        return []

    entries: deque[schemas.LogEntry] = deque(maxlen=limit)
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    entry = parse_log_line(line)
                    if not entry:
                        continue
                    if level_norm and entry.level.lower() != level_norm:
                        continue
                    entries.append(entry)
        except OSError:
            continue
    return list(entries)


class LogConnectionManager:
    """
    日志WebSocket连接管理器
    用于管理连接的WebSocket客户端并向其发送日志更新
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.log_task = None
        self.stop_flag = False

    async def connect(
        self,
        websocket: WebSocket,
        include_history: bool = True,
        level: Optional[str] = None,
    ) -> bool:
        """
        接受WebSocket连接并启动日志监控。
        历史日志只发给当前连接；实时增量由共享监控任务广播。
        客户端已断开时返回 False，调用方不要再 receive。
        """
        await websocket.accept()
        try:
            if include_history:
                await self.send_history(websocket, level=level)
        except _WS_GONE:
            return False
        if websocket.client_state != WebSocketState.CONNECTED:
            return False

        self.active_connections.append(websocket)
        if self.log_task is None or self.log_task.done():
            self.stop_flag = False
            self.log_task = asyncio.create_task(self.monitor_log_file())
        return True

    def disconnect(self, websocket: WebSocket):
        """
        断开WebSocket连接
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        if not self.active_connections:
            self.stop_flag = True

    async def send_history(self, websocket: WebSocket, level: Optional[str] = None):
        """
        向单个客户端发送最近一段历史日志，不改动服务器日志文件。
        """
        try:
            log_entries = await asyncio.to_thread(
                read_recent_logs, settings.LOGGING_LOCATION, HISTORY_LINE_LIMIT, level
            )
            if not log_entries:
                return
            if websocket.client_state != WebSocketState.CONNECTED:
                return
            await websocket.send_json(
                {"logs": [entry.model_dump() for entry in log_entries]}
            )
        except _WS_GONE:
            return
        except Exception:
            logger.exception("读取历史日志时出错")

    async def send_log(self, log_entry: schemas.LogEntry):
        """
        向所有已连接的客户端发送日志条目
        """
        disconnected_websockets = []

        for websocket in self.active_connections:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(log_entry.model_dump())
                except (WebSocketDisconnect, Exception):
                    disconnected_websockets.append(websocket)

        for websocket in disconnected_websockets:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def monitor_log_file(self):
        """
        从当前文件末尾开始跟踪新增日志，不再在监控循环里重放全量历史。
        """
        log_file_path = settings.LOGGING_LOCATION
        file_size = os.path.getsize(log_file_path) if os.path.exists(log_file_path) else 0

        while not self.stop_flag and self.active_connections:
            try:
                if not os.path.exists(log_file_path):
                    file_size = 0
                    await asyncio.sleep(0.5)
                    continue

                new_size = os.path.getsize(log_file_path)
                if new_size < file_size:
                    file_size = 0

                if new_size > file_size:
                    with open(log_file_path, "r", encoding="utf-8") as f:
                        f.seek(file_size)
                        new_content = f.read()

                    for line in new_content.splitlines():
                        entry = parse_log_line(line)
                        if entry:
                            await self.send_log(entry)

                    file_size = new_size
            except Exception:
                logger.exception("监控日志文件时出错")

            await asyncio.sleep(0.5)


log_manager = LogConnectionManager()


@router.websocket("/logs")
async def websocket_logs(
    websocket: WebSocket,
    token: str = Query(None),
    history: bool = Query(True),
    level: Optional[str] = Query(None),
):
    """
    WebSocket接口，用于实时接收日志更新。
    history=true 时额外推送最近一段历史；history=false 时只推送连接之后的新日志。
    level 指定时，历史按该级别从文件中取最近 1000 条。
    """
    if not token:
        await _reject_websocket(websocket)
        return

    token_data = await verify_ws_token(websocket, token)
    if not token_data:
        return

    connected = await log_manager.connect(
        websocket, include_history=history, level=level
    )
    if not connected:
        return
    try:
        while True:
            await websocket.receive_text()
    except _WS_GONE:
        pass
    finally:
        log_manager.disconnect(websocket)
