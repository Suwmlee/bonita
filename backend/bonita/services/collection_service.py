from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from bonita import schemas
from bonita.db.models.collection import Collection, CollectionItem
from bonita.db.models.mediaitem import MediaItem
from bonita.modules.media_service.client import SOURCE_EMBY, is_to_server
from bonita.modules.media_service.factory import require_media_client
from bonita.modules.media_service.sync import (
    add_and_sync_collection,
    add_collection_members,
    remove_collection_member,
    sync_collection_members,
    sync_whitelisted_collections,
    _refresh_collection_meta,
)
from bonita.services.mediaitem_service import MediaItemService


class CollectionService:
    """合集白名单与媒体服务器合集同步编排。"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, collection_id: int) -> Optional[Collection]:
        return self.session.query(Collection).filter(Collection.id == collection_id).first()

    def search_remote_collections(
        self, search: str = "", limit: int = 50, source: str = SOURCE_EMBY
    ) -> List[schemas.EmbyCollectionCandidate]:
        client = require_media_client(source)
        refs = client.search_collections(search.strip(), limit=limit)
        added_ids = {
            (row.source, row.external_id)
            for row in self.session.query(Collection.source, Collection.external_id).all()
        }
        results = []
        for ref in refs:
            results.append(
                schemas.EmbyCollectionCandidate(
                    source=client.source,
                    external_id=ref.remote_id,
                    name=ref.name or "",
                    child_count=int(ref.child_count or 0),
                    image_tag=ref.image_tag,
                    added=(client.source, ref.remote_id) in added_ids,
                )
            )
        return results

    def search_emby_collections(
        self, search: str = "", limit: int = 50
    ) -> List[schemas.EmbyCollectionCandidate]:
        return self.search_remote_collections(search=search, limit=limit, source=SOURCE_EMBY)

    def list_collections(self) -> List[Collection]:
        rows = self.session.query(Collection).order_by(Collection.updatetime.desc()).all()
        for row in rows:
            if not row.name or row.name == row.external_id:
                try:
                    _refresh_collection_meta(self.session, row)
                except Exception:
                    pass
        return rows

    def add_collection(
        self, external_id: str, name: Optional[str] = None, source: str = SOURCE_EMBY
    ) -> Collection:
        return add_and_sync_collection(self.session, external_id, name, source=source)

    def sync_all(self, direction: str = "from_server") -> int:
        return sync_whitelisted_collections(self.session, direction=direction)

    def sync_one(self, collection: Collection, direction: str = "from_server") -> Collection:
        return sync_collection_members(self.session, collection, direction=direction)

    def search_candidates(
        self, collection_id: int, search: str = "", limit: int = 20
    ) -> List[schemas.MediaItemWithWatches]:
        member_ids = [
            row[0]
            for row in self.session.query(CollectionItem.media_item_id).filter(
                CollectionItem.collection_id == collection_id
            ).all()
        ]
        query = self.session.query(MediaItem)
        if member_ids:
            query = query.filter(~MediaItem.id.in_(member_ids))
        query = query.filter(
            ~((MediaItem.media_type == "episode") & (
                (MediaItem.season_number < 0) | (MediaItem.episode_number < 0)
            ))
        )
        keyword = search.strip()
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    MediaItem.title.ilike(like),
                    MediaItem.original_title.ilike(like),
                    MediaItem.number.ilike(like),
                )
            )
        media_items = query.order_by(MediaItem.updatetime.desc()).limit(limit).all()
        return MediaItemService(self.session).attach_watch_data(media_items)

    def add_items(self, collection: Collection, media_item_ids: List[int]) -> Collection:
        add_collection_members(self.session, collection, media_item_ids)
        return collection

    def remove_item(self, collection: Collection, media_item_id: int) -> bool:
        return bool(remove_collection_member(self.session, collection, media_item_id))

    def get_detail(self, collection: Collection) -> Tuple[Collection, List[schemas.MediaItemWithWatches]]:
        if not collection.name or collection.name == collection.external_id:
            try:
                _refresh_collection_meta(self.session, collection)
            except Exception:
                pass
        media_items = (
            self.session.query(MediaItem)
            .join(CollectionItem, CollectionItem.media_item_id == MediaItem.id)
            .filter(CollectionItem.collection_id == collection.id)
            .order_by(MediaItem.title.asc())
            .all()
        )
        return collection, MediaItemService(self.session).attach_watch_data(media_items)

    def delete_collection(self, collection: Collection) -> None:
        self.session.delete(collection)
        self.session.commit()

    @staticmethod
    def sync_message(direction: str, synced: int) -> str:
        label = "媒体服务器"
        if is_to_server(direction):
            return f"已回写 {synced} 个合集到 {label}"
        return f"已从 {label} 拉取 {synced} 个合集"
