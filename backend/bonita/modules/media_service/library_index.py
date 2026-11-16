"""媒体库内存索引，供合集回写批量匹配。"""

import logging
import os

from bonita.modules.media_service.client import RemoteItem
from bonita.modules.media_service.path_match import normalize_path, remote_file_paths

logger = logging.getLogger(__name__)


class LibraryIndex:
    """库内条目缓存。查询参数与 EmbyClient.query_items 相同，挑选仍走原来的函数。"""

    def __init__(self, items):
        self.items = list(items or [])

    def query_items(
        self,
        item_types,
        search_term=None,
        imdb_id=None,
        tmdb_id=None,
        tvdb_id=None,
        parent_id=None,
        limit=25,
    ):
        types = set(item_types or [])
        term = (search_term or "").strip().lower()
        matched = []
        for item in self.items:
            if types and item.item_type not in types:
                continue
            if parent_id and item.series_remote_id != parent_id:
                continue
            if imdb_id and item.imdb_id != imdb_id:
                continue
            if tmdb_id and str(item.tmdb_id or "") != str(tmdb_id):
                continue
            if tvdb_id and item.tvdb_id != tvdb_id:
                continue
            if term and _search_rank(item, term) is None:
                continue
            matched.append(item)
        if term:
            matched.sort(key=lambda item: _search_rank(item, term))
        if limit and limit > 0:
            return matched[:limit]
        return matched


def _search_rank(item: RemoteItem, term: str):
    """越小越靠前。对不上返回 None。标题、原标题和路径都参与，文件名搜索才能对上。"""
    title = (item.title or "").strip().lower()
    original = (item.original_title or "").strip().lower()
    paths = [normalize_path(path) for path in remote_file_paths(item)]
    names = [title, original]
    names.extend(os.path.basename(path) for path in paths if path)
    if term in names or term in paths:
        return 0
    if any(name.startswith(term) for name in names if name):
        return 1
    if any(term in name for name in names if name) or any(term in path for path in paths):
        return 2
    return None


def load_library_index(client):
    try:
        items = client.list_index_items()
    except Exception as e:
        logger.warning(f"  ⊘ 库内索引拉取失败，改为按条查找: {e}")
        return None
    logger.info(f"  → 库内索引 {len(items)} 条")
    return LibraryIndex(items)
