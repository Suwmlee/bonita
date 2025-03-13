from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class DirectoryBrowseRequest(BaseModel):
    """
    文件浏览请求参数
    """
    directory_path: Optional[str] = None


class FileInfo(BaseModel):
    """
    文件或目录信息
    """
    name: str
    path: str
    is_dir: bool
    size: int = 0
    modified_time: Optional[datetime] = None


class FileListResponse(BaseModel):
    """
    目录内文件列表响应
    """
    data: List[FileInfo]
    current_path: str
    parent_path: Optional[str] = None 