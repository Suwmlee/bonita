from typing import List, Optional

from sqlalchemy.orm import Session

from bonita import schemas
from bonita.db.models.playlist import Playlist, PlaylistItem
from bonita.modules.media_service.client import SOURCE_PLEX
from bonita.modules.media_service.factory import require_plex_client
from bonita.modules.media_service.playlist_sync import (
    add_and_sync_playlist,
    refresh_playlist_meta,
    sync_playlist_members,
    sync_whitelisted_playlists,
)
from bonita.services.celery_service import CeleryTaskService, TASK_PLAYLIST_SYNC
from bonita.tasks import celery_sync_playlist


class PlaylistService:
    """播放列表白名单 CRUD，同步实现在 playlist_sync。"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, playlist_id: int) -> Optional[Playlist]:
        return self.session.query(Playlist).filter(Playlist.id == playlist_id).first()

    def search_remote_playlists(
        self, search: str = "", limit: int = 50, source: str = SOURCE_PLEX
    ) -> List[schemas.PlexPlaylistCandidate]:
        if source != SOURCE_PLEX:
            raise RuntimeError(f"暂不支持的播放列表源: {source}")
        client = require_plex_client()
        refs = client.list_audio_playlists(search.strip(), limit=limit)
        added_ids = {
            (row.source, row.external_id)
            for row in self.session.query(Playlist.source, Playlist.external_id).all()
        }
        results = []
        for ref in refs:
            results.append(
                schemas.PlexPlaylistCandidate(
                    source=SOURCE_PLEX,
                    external_id=ref.remote_id,
                    rating_key=ref.rating_key,
                    name=ref.name or "",
                    leaf_count=int(ref.leaf_count or 0),
                    smart=bool(ref.smart),
                    added=(SOURCE_PLEX, ref.remote_id) in added_ids,
                )
            )
        return results

    def list_playlists(self) -> List[Playlist]:
        rows = self.session.query(Playlist).order_by(Playlist.updatetime.desc()).all()
        for row in rows:
            if not row.name or row.name == row.external_id:
                try:
                    refresh_playlist_meta(self.session, row)
                except Exception:
                    pass
        return rows

    def add_playlist(
        self,
        external_id: str,
        name: Optional[str] = None,
        rating_key: Optional[str] = None,
        source: str = SOURCE_PLEX,
    ) -> Playlist:
        return add_and_sync_playlist(
            self.session,
            external_id,
            name=name,
            rating_key=rating_key,
            source=source,
        )

    def sync_all(self, direction: str = "from_server") -> int:
        return sync_whitelisted_playlists(self.session, direction=direction)

    def sync_one(self, playlist: Playlist, direction: str = "from_server") -> Playlist:
        return sync_playlist_members(self.session, playlist, direction=direction)

    def enqueue_sync(
        self, playlist_id: Optional[int] = None, direction: str = "from_server"
    ) -> schemas.TaskStatus:
        detail = f"{playlist_id if playlist_id is not None else 'all'}|{direction}"
        return CeleryTaskService(self.session).enqueue_unique(
            celery_sync_playlist,
            TASK_PLAYLIST_SYNC,
            detail=detail,
            name="播放列表同步",
            playlist_id=playlist_id,
            direction=direction,
        )

    def get_detail(self, playlist: Playlist) -> tuple:
        if not playlist.name or playlist.name == playlist.external_id:
            try:
                refresh_playlist_meta(self.session, playlist)
            except Exception:
                pass
        items = (
            self.session.query(PlaylistItem)
            .filter(PlaylistItem.playlist_id == playlist.id)
            .order_by(PlaylistItem.sort_index.asc(), PlaylistItem.id.asc())
            .all()
        )
        return playlist, items

    def delete_playlist(self, playlist: Playlist) -> None:
        self.session.delete(playlist)
        self.session.commit()
