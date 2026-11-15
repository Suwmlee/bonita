import logging
import re
from typing import Any, Dict, List, Optional, Union
from xml.etree import ElementTree

import requests

from bonita.modules.media_service.client import (
    ITEM_EPISODE,
    ITEM_MOVIE,
    ITEM_SEASON,
    ITEM_SERIES,
    RATING_FAVORITE_WRITE,
    SOURCE_PLEX,
    WEBHOOK_IGNORED,
    CollectionRef,
    MediaServerClient,
    RemoteItem,
    WatchState,
    WebhookEvent,
    is_favorite_rating,
)
from bonita.utils.singleton import Singleton

logger = logging.getLogger(__name__)

_PAGE_SIZE = 200
_PLEX_TYPE_MOVIE = "1"
_PLEX_TYPE_SHOW = "2"
_PLEX_TYPE_SEASON = "3"
_PLEX_TYPE_EPISODE = "4"
_TYPE_TO_PLEX = {
    ITEM_MOVIE: _PLEX_TYPE_MOVIE,
    ITEM_SERIES: _PLEX_TYPE_SHOW,
    ITEM_SEASON: _PLEX_TYPE_SEASON,
    ITEM_EPISODE: _PLEX_TYPE_EPISODE,
}
def _as_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value, default=-1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ms_to_seconds(value) -> int:
    ms = _as_int(value, default=0)
    if ms <= 0:
        return 0
    return int(ms / 1000)


def _media_paths(raw: dict) -> list:
    paths = []
    seen = set()
    media_list = raw.get("Media")
    if isinstance(media_list, dict):
        media_list = [media_list]
    for media in media_list or []:
        if not isinstance(media, dict):
            continue
        parts = media.get("Part")
        if isinstance(parts, dict):
            parts = [parts]
        for part in parts or []:
            if not isinstance(part, dict):
                continue
            path = _as_str(part.get("file"))
            key = path.replace("\\", "/").rstrip("/").lower()
            if not key or key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return paths


def _provider_ids_from_raw(raw: dict) -> Dict[str, str]:
    providers: Dict[str, str] = {}

    def add(kind: str, value: str):
        value = _as_str(value)
        if not value or kind in providers:
            return
        if kind == "imdb" and not value.lower().startswith("tt"):
            value = f"tt{value}" if value.isdigit() else value
        providers[kind] = value

    guids = raw.get("Guid") or []
    if isinstance(guids, dict):
        guids = [guids]
    for entry in guids:
        gid = _as_str(entry.get("id") if isinstance(entry, dict) else entry)
        if gid.startswith("imdb://"):
            add("imdb", gid.split("://", 1)[1].split("?", 1)[0])
        elif gid.startswith("tmdb://"):
            add("tmdb", gid.split("://", 1)[1].split("?", 1)[0])
        elif gid.startswith("tvdb://"):
            add("tvdb", gid.split("://", 1)[1].split("?", 1)[0])

    legacy = _as_str(raw.get("guid"))
    if legacy:
        patterns = (
            (r"imdb://(tt\d+)", "imdb"),
            (r"agents\.imdb://(tt\d+)", "imdb"),
            (r"themoviedb://(\d+)", "tmdb"),
            (r"agents\.themoviedb://(\d+)", "tmdb"),
            (r"thetvdb://(\d+)", "tvdb"),
            (r"agents\.thetvdb://(\d+)", "tvdb"),
        )
        for pattern, kind in patterns:
            match = re.search(pattern, legacy, re.I)
            if match:
                add(kind, match.group(1))
    return providers


class PlexClient(MediaServerClient, metaclass=Singleton):
    """Plex 适配：电影/剧观看同步 + 普通 audio 播放列表拉取。"""

    source = SOURCE_PLEX

    def __init__(self):
        self.plex_host = None
        self.plex_token = None
        self.machine_identifier = None
        self.headers = {}
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def initialize(self, host: str, apikey: str, user: str = "") -> bool:
        plex_host, plex_token = (host or "").rstrip("/"), apikey or ""
        if (
            self._initialized
            and self.plex_host == plex_host
            and self.plex_token == plex_token
        ):
            return True

        self.plex_host = plex_host or None
        self.plex_token = plex_token
        self.headers = {
            "Accept": "application/json",
            "X-Plex-Token": self.plex_token,
            "X-Plex-Client-Identifier": "bonita",
            "X-Plex-Product": "Bonita",
            "X-Plex-Version": "1.0",
        }
        if not self.plex_host or not self.plex_token:
            logger.warning("Plex service initialized with missing host or token")
            self._initialized = False
            return False
        try:
            identity = self._make_request("get", "/identity")
            container = self._container(identity) or {}
            self.machine_identifier = _as_str(
                container.get("machineIdentifier") or container.get("MachineIdentifier")
            ) or None
            if not self.machine_identifier and isinstance(identity, dict):
                self.machine_identifier = _as_str(identity.get("machineIdentifier")) or None
            self._initialized = True
        except Exception as e:
            logger.error(f"Error initializing Plex service: {e}")
            self._initialized = False
            return False
        logger.info(f"Plex service initialized with host: {self.plex_host}")
        return True

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
        if not self.plex_host or not self.plex_token:
            raise RuntimeError("Plex host or token not configured")
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        url = f"{self.plex_host}{endpoint}"
        query = dict(params or {})
        query.setdefault("X-Plex-Token", self.plex_token)
        response = requests.request(
            method.upper(),
            url,
            headers=self.headers,
            params=query,
            timeout=60,
        )
        response.raise_for_status()
        if not response.content:
            return None
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "json" in content_type:
            return response.json()
        root = ElementTree.fromstring(response.content)
        return {root.tag: root.attrib}

    @staticmethod
    def _container(payload) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        container = payload.get("MediaContainer")
        if isinstance(container, dict):
            return container
        return payload if "size" in payload or "machineIdentifier" in payload else None

    @staticmethod
    def _metadata_list(payload) -> List[Dict[str, Any]]:
        container = PlexClient._container(payload) or {}
        items = container.get("Metadata") or container.get("Playlist") or container.get("Directory") or []
        if isinstance(items, dict):
            return [items]
        return list(items or [])

    def _paged_metadata(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        start = 0
        base = dict(params or {})
        while True:
            page_params = dict(base)
            page_params["X-Plex-Container-Start"] = start
            page_params["X-Plex-Container-Size"] = _PAGE_SIZE
            page_params.setdefault("includeGuids", 1)
            raw = self._make_request("get", endpoint, params=page_params)
            page = self._metadata_list(raw)
            items.extend(page)
            if len(page) < _PAGE_SIZE:
                break
            start += _PAGE_SIZE
            if start >= 100000:
                logger.warning(f"Plex 分页超过 100000 条，停止继续拉取 {endpoint}")
                break
        return items

    def _library_sections(self) -> List[Dict[str, Any]]:
        raw = self._make_request("get", "/library/sections")
        container = self._container(raw) or {}
        dirs = container.get("Directory") or []
        if isinstance(dirs, dict):
            return [dirs]
        return list(dirs or [])

    def to_remote_item(self, raw: Optional[dict]) -> Optional[RemoteItem]:
        if not isinstance(raw, dict):
            return None
        rating_key = _as_str(raw.get("ratingKey"))
        if not rating_key:
            return None
        plex_type = _as_str(raw.get("type")).lower()
        type_map = {
            "movie": ITEM_MOVIE,
            "show": ITEM_SERIES,
            "season": ITEM_SEASON,
            "episode": ITEM_EPISODE,
        }
        item_type = type_map.get(plex_type)
        if not item_type:
            return None

        season = -1
        episode = -1
        series_remote_id = None
        series_name = ""
        if item_type == ITEM_EPISODE:
            season = _as_int(raw.get("parentIndex"))
            episode = _as_int(raw.get("index"))
            series_remote_id = _as_str(raw.get("grandparentRatingKey")) or None
            series_name = _as_str(raw.get("grandparentTitle"))
        elif item_type == ITEM_SEASON:
            season = _as_int(raw.get("index"))
            series_remote_id = _as_str(raw.get("parentRatingKey")) or None
            series_name = _as_str(raw.get("parentTitle"))
        elif item_type == ITEM_SERIES:
            series_remote_id = rating_key

        paths = _media_paths(raw)
        path = paths[0] if paths else None
        # show/season 有时只有目录路径
        if not path:
            path = _as_str(raw.get("path")) or None

        duration = _ms_to_seconds(raw.get("duration"))
        view_count = max(0, _as_int(raw.get("viewCount"), default=0))
        played = view_count > 0
        position_seconds = _ms_to_seconds(raw.get("viewOffset"))
        play_progress = 100.0 if played else 0.0
        if position_seconds > 0 and duration > 0:
            play_progress = min(100.0, (position_seconds / duration) * 100)
        user_rating = _as_float(raw.get("userRating"), default=0.0)
        rating = user_rating if user_rating > 0 else None

        return RemoteItem(
            source=SOURCE_PLEX,
            remote_id=rating_key,
            item_type=item_type,
            title=_as_str(raw.get("title")),
            original_title=_as_str(raw.get("originalTitle")),
            path=path,
            source_paths=paths,
            provider_ids=_provider_ids_from_raw(raw),
            season=season,
            episode=episode,
            series_remote_id=series_remote_id,
            series_name=series_name,
            watch=WatchState(
                played=played,
                favorite=is_favorite_rating(rating),
                play_count=view_count or (1 if played else 0),
                position_seconds=position_seconds,
                duration_seconds=duration,
                play_progress=play_progress,
                rating=rating,
            ),
            image_tag=_as_str(raw.get("thumb")) or None,
            child_count=max(0, _as_int(raw.get("leafCount"), default=0)),
            is_folder=item_type in {ITEM_SERIES, ITEM_SEASON},
        )

    def list_user_items(self) -> List[RemoteItem]:
        items: List[RemoteItem] = []
        for section in self._library_sections():
            section_type = _as_str(section.get("type")).lower()
            section_key = _as_str(section.get("key"))
            if not section_key:
                continue
            endpoint = f"/library/sections/{section_key}/all"
            if section_type == "movie":
                for raw in self._paged_metadata(endpoint, {"type": _PLEX_TYPE_MOVIE}):
                    remote = self.to_remote_item(raw)
                    if remote:
                        items.append(remote)
            elif section_type == "show":
                for plex_type in (_PLEX_TYPE_SHOW, _PLEX_TYPE_SEASON, _PLEX_TYPE_EPISODE):
                    for raw in self._paged_metadata(endpoint, {"type": plex_type}):
                        remote = self.to_remote_item(raw)
                        if remote:
                            items.append(remote)
            else:
                logger.debug(f"Skipping Plex library {_as_str(section.get('title'))} type={section_type}")
        return items

    def list_index_items(self) -> List[RemoteItem]:
        return self.list_user_items()

    def get_item(self, item_id: str) -> Optional[RemoteItem]:
        item_id = _as_str(item_id)
        if not item_id:
            return None
        try:
            raw = self._make_request(
                "get",
                f"/library/metadata/{item_id}",
                params={"includeGuids": 1},
            )
            for row in self._metadata_list(raw):
                remote = self.to_remote_item(row)
                if remote:
                    return remote
        except Exception as e:
            logger.warning(f"获取 Plex 条目失败 {item_id}: {e}")
        return None

    def get_user_item(self, item_id: str) -> Optional[RemoteItem]:
        return self.get_item(item_id)

    def query_items(
        self,
        item_types: List[str],
        search_term: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[str] = None,
        tvdb_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        limit: int = 25,
    ) -> List[RemoteItem]:
        results: List[RemoteItem] = []
        plex_types = [
            _TYPE_TO_PLEX[t] for t in item_types if t in _TYPE_TO_PLEX
        ] or [_PLEX_TYPE_MOVIE, _PLEX_TYPE_SHOW, _PLEX_TYPE_EPISODE]

        if parent_id:
            try:
                raw = self._make_request(
                    "get",
                    f"/library/metadata/{parent_id}/children",
                    params={"includeGuids": 1, "X-Plex-Container-Size": limit},
                )
                for row in self._metadata_list(raw):
                    remote = self.to_remote_item(row)
                    if remote and remote.item_type in set(item_types or [remote.item_type]):
                        results.append(remote)
                        if len(results) >= limit:
                            return results
            except Exception as e:
                logger.warning(f"Plex parent 查询失败 {parent_id}: {e}")

        term = (search_term or "").strip()
        if term:
            try:
                raw = self._make_request(
                    "get",
                    "/search",
                    params={
                        "query": term,
                        "includeGuids": 1,
                        "limit": max(limit, 25),
                    },
                )
                for row in self._metadata_list(raw):
                    remote = self.to_remote_item(row)
                    if not remote or remote.item_type not in set(item_types or [remote.item_type]):
                        continue
                    results.append(remote)
                    if len(results) >= limit:
                        return results
            except Exception as e:
                logger.warning(f"Plex 搜索失败: {e}")

        # 按库扫一遍做 provider / 弱匹配兜底
        if imdb_id or tmdb_id or tvdb_id or (not results and term):
            for section in self._library_sections():
                section_type = _as_str(section.get("type")).lower()
                section_key = _as_str(section.get("key"))
                if not section_key:
                    continue
                wanted = []
                if section_type == "movie" and _PLEX_TYPE_MOVIE in plex_types:
                    wanted = [_PLEX_TYPE_MOVIE]
                elif section_type == "show":
                    wanted = [t for t in plex_types if t in {_PLEX_TYPE_SHOW, _PLEX_TYPE_SEASON, _PLEX_TYPE_EPISODE}]
                for plex_type in wanted:
                    for row in self._paged_metadata(
                        f"/library/sections/{section_key}/all",
                        {"type": plex_type},
                    ):
                        remote = self.to_remote_item(row)
                        if not remote:
                            continue
                        if imdb_id and remote.imdb_id == imdb_id:
                            results.append(remote)
                        elif tmdb_id and remote.tmdb_id == str(tmdb_id):
                            results.append(remote)
                        elif tvdb_id and remote.tvdb_id == str(tvdb_id):
                            results.append(remote)
                        elif term and term.lower() in (remote.title or "").lower():
                            results.append(remote)
                        if len(results) >= limit:
                            return results
        return results[:limit]

    def search_collections(self, search: str = "", limit: int = 50) -> List[CollectionRef]:
        return []

    def get_collection_items(self, collection_id: str) -> List[RemoteItem]:
        return []

    def add_items_to_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        return 0, len(item_ids or [])

    def remove_items_from_collection(self, collection_id: str, item_ids: List[str]) -> tuple:
        return 0, len(item_ids or [])

    def mark_as_played(self, item_id: str):
        item_id = _as_str(item_id)
        if not item_id:
            return
        self._make_request(
            "get",
            "/:/scrobble",
            params={
                "identifier": "com.plexapp.plugins.library",
                "key": item_id,
            },
        )

    def mark_as_unplayed(self, item_id: str):
        item_id = _as_str(item_id)
        if not item_id:
            return
        self._make_request(
            "get",
            "/:/unscrobble",
            params={
                "identifier": "com.plexapp.plugins.library",
                "key": item_id,
            },
        )

    def mark_as_favorite(self, item_id: str):
        item_id = _as_str(item_id)
        if not item_id:
            return
        self._make_request(
            "get",
            "/:/rate",
            params={
                "identifier": "com.plexapp.plugins.library",
                "key": item_id,
                "rating": int(RATING_FAVORITE_WRITE),
            },
        )

    def unmark_as_favorite(self, item_id: str):
        item_id = _as_str(item_id)
        if not item_id:
            return
        self._make_request(
            "get",
            "/:/rate",
            params={
                "identifier": "com.plexapp.plugins.library",
                "key": item_id,
                "rating": 0,
            },
        )

    def set_user_rating(self, item_id: str, rating: float):
        """写入 Plex userRating（0–10）。0 表示清除。"""
        item_id = _as_str(item_id)
        if not item_id:
            return
        value = 0
        try:
            value = int(round(float(rating)))
        except (TypeError, ValueError):
            value = 0
        value = max(0, min(10, value))
        self._make_request(
            "get",
            "/:/rate",
            params={
                "identifier": "com.plexapp.plugins.library",
                "key": item_id,
                "rating": value,
            },
        )

    def trigger_library_scan(self):
        for section in self._library_sections():
            section_key = _as_str(section.get("key"))
            if not section_key:
                continue
            try:
                self._make_request("get", f"/library/sections/{section_key}/refresh")
            except Exception as e:
                logger.warning(f"刷新 Plex 库失败 {section_key}: {e}")

    def get_item_image_url(self, item_id: str, image_tag: str = None, size: str = "w500") -> Optional[str]:
        thumb = image_tag or ""
        if not thumb and item_id:
            item = self.get_item(item_id)
            thumb = (item.image_tag if item else "") or ""
        if not thumb or not self.plex_host:
            return None
        if thumb.startswith("http"):
            return thumb
        width = size.split("w")[-1] if size else ""
        url = f"{self.plex_host}{thumb}"
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}X-Plex-Token={self.plex_token}"
        if width.isdigit():
            url += f"&width={width}&height={width}&minSize=1"
        return url

    def get_poster_url(
        self,
        title: str,
        imdb_id: str = None,
        tmdb_id=None,
        size: str = "w500",
    ) -> Optional[str]:
        items = self.query_items(
            [ITEM_MOVIE, ITEM_SERIES],
            search_term=title,
            imdb_id=imdb_id,
            tmdb_id=str(tmdb_id) if tmdb_id else None,
            limit=10,
        )
        if not items:
            return None
        return self.get_item_image_url(items[0].remote_id, items[0].image_tag, size=size)

    def parse_webhook(self, payload: dict) -> WebhookEvent:
        return WebhookEvent(kind=WEBHOOK_IGNORED, raw_event="")
