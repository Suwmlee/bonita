import os
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union


class torrent_info:
    id: Union[int, str]
    name: str
    hash: str
    downloadDir: str
    error: int
    errorString: str


class BaseDownloadClient(ABC):
    """下载客户端公共接口。路径映射和按名称/路径查找与具体客户端无关。"""

    def __init__(self):
        self.source_path = ""
        self.dest_path = ""

    @abstractmethod
    def initialize(
        self,
        url: str,
        username: str,
        password: str,
        source_path: str = "",
        dest_path: str = "",
    ) -> bool:
        """使用连接参数初始化客户端。"""
        pass

    @abstractmethod
    def login(self) -> Optional[Any]:
        """登录客户端，成功时返回会话，失败时返回 None。"""
        pass

    @abstractmethod
    def getTorrents(
        self,
        ids: Optional[Union[str, int, List[Union[str, int]]]] = None,
    ) -> List[torrent_info]:
        """获取种子列表。ids 为空时返回全部。"""
        pass

    @abstractmethod
    def deleteTorrent(self, torrent_id: Union[int, str], delete: bool = False) -> None:
        """移除种子。delete 为 True 时同时删除数据。"""
        pass

    def map_path(self, path: str, inverse: bool = False) -> str:
        """在下载器路径与本机路径之间转换。"""
        if not self.source_path or not self.dest_path or not path:
            return path
        if inverse:
            return path.replace(self.source_path, self.dest_path)
        return path.replace(self.dest_path, self.source_path)

    def searchByName(
        self,
        name: str,
        cached_torrents: Optional[List[torrent_info]] = None,
    ) -> List[torrent_info]:
        torrents = cached_torrents if cached_torrents is not None else self.getTorrents()
        return [torrent for torrent in torrents if torrent.name == name]

    def searchByPath(
        self,
        path: str,
        cached_torrents: Optional[List[torrent_info]] = None,
    ) -> List[torrent_info]:
        """按路径逐级向上匹配种子名称，最多 3 级。"""
        path = self.map_path(path)
        for _ in range(3):
            name = os.path.basename(path)
            if not name:
                break
            matched = self.searchByName(name, cached_torrents)
            if matched:
                return matched
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        return []
