from typing import Optional, Union
from pydantic import BaseModel


class Response(BaseModel):
    # 状态
    success: bool = True
    # 消息文本
    message: Optional[str] = None
    # 数据
    data: Optional[Union[dict, list]] = {}


class StatusResponse(BaseModel):
    status: str
    version: str
