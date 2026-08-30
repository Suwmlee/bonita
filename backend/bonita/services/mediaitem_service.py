from typing import List, Optional, Tuple

from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from bonita import schemas
from bonita.db.models.collection import CollectionItem
from bonita.db.models.mediaitem import MediaItem
from bonita.db.models.watch_history import WatchHistory
from bonita.services.metadata_service import MetadataService


class MediaItemService:
    """媒体项查询、观看数据装配与维护。"""

    WATCH_FIELDS = {"watched", "favorite", "play_progress", "duration", "has_rating", "user_rating"}

    def __init__(self, session: Session):
        self.session = session

    def _series_info_map(self, media_items: List[MediaItem]) -> dict:
        series_ids = {
            item.series_id for item in media_items
            if item.media_type == "episode" and item.series_id
        }
        if not series_ids:
            return {}
        series_rows = self.session.query(MediaItem).filter(MediaItem.id.in_(series_ids)).all()
        favorite_rows = self.session.query(WatchHistory.media_item_id, WatchHistory.favorite).filter(
            WatchHistory.media_item_id.in_(series_ids)
        ).all()
        favorite_map = {media_item_id: bool(favorite) for media_item_id, favorite in favorite_rows}
        return {
            row.id: {
                "imdb_id": row.imdb_id,
                "tmdb_id": row.tmdb_id,
                "favorite": favorite_map.get(row.id, False),
            }
            for row in series_rows
        }

    def _series_poster_ids(self, media_item: MediaItem, series_map: dict) -> tuple:
        if media_item.media_type != "episode" or not media_item.series_id:
            return None, None
        series = series_map.get(media_item.series_id)
        if not series:
            return None, None
        return series.get("imdb_id"), series.get("tmdb_id")

    def _remote_item_id_map(self, media_items: List[MediaItem]) -> dict:
        ids = [item.id for item in media_items]
        if not ids:
            return {}
        rows = self.session.query(CollectionItem.media_item_id, CollectionItem.external_item_id).filter(
            CollectionItem.media_item_id.in_(ids),
            CollectionItem.external_item_id.isnot(None),
            CollectionItem.external_item_id != "",
        ).all()
        result = {}
        for media_item_id, external_item_id in rows:
            if media_item_id not in result:
                result[media_item_id] = external_item_id
        return result

    def _favorited_series_ids(self) -> List[int]:
        rows = (
            self.session.query(WatchHistory.media_item_id)
            .join(MediaItem, MediaItem.id == WatchHistory.media_item_id)
            .filter(MediaItem.media_type == "tvshow", WatchHistory.favorite.is_(True))
            .all()
        )
        return [row[0] for row in rows]

    def attach_watch_data(self, media_items: List[MediaItem]) -> List[schemas.MediaItemWithWatches]:
        """给媒体项列表附上观看/收藏和海报用的系列 ID。"""
        if not media_items:
            return []
        ids = [item.id for item in media_items]
        histories = self.session.query(WatchHistory).filter(WatchHistory.media_item_id.in_(ids)).all()
        hist_map = {history.media_item_id: history for history in histories}
        metadata_service = MetadataService(self.session)
        crop_map = metadata_service.get_crop_by_numbers([item.number for item in media_items])
        series_map = self._series_info_map(media_items)
        remote_id_map = self._remote_item_id_map(media_items)
        items = []
        for media_item in media_items:
            history = hist_map.get(media_item.id)
            item_dict = schemas.MediaItemInDB.model_validate(media_item)
            series_imdb_id, series_tmdb_id = self._series_poster_ids(media_item, series_map)
            series_favorite = bool(
                media_item.series_id and series_map.get(media_item.series_id, {}).get("favorite")
            )
            favorite = bool(history.favorite) if history else False
            userdata = schemas.UserWatchData(
                favorite=favorite or series_favorite,
                watched=(history.watched if history else False) or False,
                total_plays=(history.watch_count if history else 0) or 0,
                play_progress=history.play_progress if history else None,
                duration=history.duration if history else None,
                has_rating=(history.has_rating if history else False) or False,
                user_rating=history.rating if history else None,
                last_played=history.updatetime if history else None,
                watch_updatetime=history.updatetime if history else None,
            )
            remote_id = remote_id_map.get(media_item.id)
            items.append(
                schemas.MediaItemWithWatches(
                    **item_dict.model_dump(),
                    userdata=userdata,
                    crop=metadata_service.resolve_crop(media_item.number, crop_map),
                    series_imdb_id=series_imdb_id,
                    series_tmdb_id=series_tmdb_id,
                    external_item_id=remote_id,
                    emby_item_id=remote_id,
                )
            )
        return items

    def list_media_items(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        media_type: Optional[str] = None,
        sort_by: str = "updatetime",
        sort_desc: bool = True,
        has_number: Optional[bool] = None,
        watched: Optional[bool] = None,
        favorite: Optional[bool] = None,
    ) -> Tuple[List[schemas.MediaItemWithWatches], int]:
        watch_info = (
            self.session.query(
                WatchHistory.media_item_id,
                func.max(WatchHistory.watched).label("watched"),
                func.max(WatchHistory.favorite).label("favorite"),
                func.sum(WatchHistory.watch_count).label("total_plays"),
                func.max(WatchHistory.play_progress).label("play_progress"),
                func.max(WatchHistory.duration).label("duration"),
                func.max(WatchHistory.has_rating).label("has_rating"),
                func.max(WatchHistory.rating).label("rating"),
                func.max(WatchHistory.updatetime).label("watch_updatetime"),
            )
            .group_by(WatchHistory.media_item_id)
            .subquery()
        )

        query = (
            self.session.query(
                MediaItem,
                watch_info.c.favorite,
                watch_info.c.watched,
                watch_info.c.total_plays,
                watch_info.c.play_progress,
                watch_info.c.duration,
                watch_info.c.has_rating,
                watch_info.c.rating,
                watch_info.c.watch_updatetime
            )
            .outerjoin(watch_info, MediaItem.id == watch_info.c.media_item_id)
        )

        if search:
            query = query.filter(
                MediaItem.title.ilike(f"%{search}%") |
                MediaItem.original_title.ilike(f"%{search}%") |
                MediaItem.number.ilike(f"%{search}%")
            )

        if media_type == "tvshow":
            query = query.filter(MediaItem.media_type == "episode")
        elif media_type:
            query = query.filter(MediaItem.media_type == media_type)
        else:
            query = query.filter(MediaItem.media_type != "tvshow")

        query = query.filter(
            (MediaItem.media_type != "episode")
            | (
                (MediaItem.season_number >= 0)
                & (MediaItem.episode_number >= 0)
            )
        )

        if has_number is not None:
            if has_number:
                query = query.filter(MediaItem.number.isnot(None), MediaItem.number != "")
            else:
                query = query.filter((MediaItem.number.is_(None)) | (MediaItem.number == ""))

        if watched is not None:
            if watched:
                query = query.filter(watch_info.c.watched > 0)
            else:
                query = query.filter((watch_info.c.watched == 0) | (watch_info.c.watched.is_(None)))

        if favorite is not None:
            favorited_series_ids = self._favorited_series_ids()
            if favorite:
                if favorited_series_ids:
                    query = query.filter(
                        (watch_info.c.favorite > 0)
                        | MediaItem.series_id.in_(favorited_series_ids)
                    )
                else:
                    query = query.filter(watch_info.c.favorite > 0)
            else:
                if favorited_series_ids:
                    query = query.filter(
                        ((watch_info.c.favorite == 0) | watch_info.c.favorite.is_(None))
                        & (
                            MediaItem.series_id.is_(None)
                            | ~MediaItem.series_id.in_(favorited_series_ids)
                        )
                    )
                else:
                    query = query.filter(
                        (watch_info.c.favorite == 0) | watch_info.c.favorite.is_(None)
                    )

        count = query.count()
        sort_column = getattr(MediaItem, sort_by, MediaItem.updatetime)
        query = query.order_by(desc(sort_column) if sort_desc else asc(sort_column))
        results = query.offset(skip).limit(limit).all()

        metadata_service = MetadataService(self.session)
        crop_map = metadata_service.get_crop_by_numbers(
            [media_item.number for media_item, *_ in results],
        )
        media_items = [media_item for media_item, *_ in results]
        series_map = self._series_info_map(media_items)
        remote_id_map = self._remote_item_id_map(media_items)

        items = []
        for (
            media_item, item_favorite, item_watched, total_plays, play_progress,
            duration, has_rating, rating, watch_updatetime,
        ) in results:
            item_dict = schemas.MediaItemInDB.model_validate(media_item)
            series_imdb_id, series_tmdb_id = self._series_poster_ids(media_item, series_map)
            series_favorite = bool(
                media_item.series_id and series_map.get(media_item.series_id, {}).get("favorite")
            )
            userdata = schemas.UserWatchData(
                favorite=bool(item_favorite) or series_favorite,
                watched=item_watched or False,
                total_plays=total_plays or 0,
                play_progress=play_progress,
                duration=duration,
                has_rating=has_rating or False,
                user_rating=rating,
                last_played=watch_updatetime,
                watch_updatetime=watch_updatetime
            )
            remote_id = remote_id_map.get(media_item.id)
            items.append(
                schemas.MediaItemWithWatches(
                    **item_dict.model_dump(),
                    userdata=userdata,
                    crop=metadata_service.resolve_crop(media_item.number, crop_map),
                    series_imdb_id=series_imdb_id,
                    series_tmdb_id=series_tmdb_id,
                    external_item_id=remote_id,
                    emby_item_id=remote_id,
                )
            )
        return items, count

    def get_by_id(self, media_id: int) -> Optional[MediaItem]:
        return self.session.query(MediaItem).filter(MediaItem.id == media_id).first()

    def get_with_watch_data(self, media_id: int) -> Optional[schemas.MediaItemWithWatches]:
        media_item = self.get_by_id(media_id)
        if not media_item:
            return None
        return self.attach_watch_data([media_item])[0]

    def create_media_item(self, payload: dict) -> MediaItem:
        media_item = MediaItem(**payload)
        self.session.add(media_item)
        self.session.commit()
        self.session.refresh(media_item)
        return media_item

    def update_media_item(
        self, media_id: int, update_data: dict
    ) -> Optional[schemas.MediaItemWithWatches]:
        media_item = self.get_by_id(media_id)
        if not media_item:
            return None

        watch_data = {k: v for k, v in update_data.items() if k in self.WATCH_FIELDS}
        media_data = {k: v for k, v in update_data.items() if k not in self.WATCH_FIELDS}

        for field, value in media_data.items():
            setattr(media_item, field, value)

        if watch_data:
            watch_history = self.session.query(WatchHistory).filter(
                WatchHistory.media_item_id == media_id
            ).first()
            if not watch_history:
                watch_history = WatchHistory(media_item_id=media_id)
                self.session.add(watch_history)
            if "watched" in watch_data:
                watch_history.watched = watch_data["watched"]
            if "favorite" in watch_data:
                watch_history.favorite = watch_data["favorite"]
            if "play_progress" in watch_data:
                watch_history.play_progress = watch_data["play_progress"]
            if "duration" in watch_data:
                watch_history.duration = watch_data["duration"]
            if "has_rating" in watch_data:
                watch_history.has_rating = watch_data["has_rating"]
            if "user_rating" in watch_data:
                watch_history.rating = watch_data["user_rating"]

        self.session.commit()
        self.session.refresh(media_item)
        return self.attach_watch_data([media_item])[0]

    def delete_media_item(self, media_id: int) -> Optional[dict]:
        media_item = self.get_by_id(media_id)
        if not media_item:
            return None
        watch_history_deleted = self.session.query(WatchHistory).filter(
            WatchHistory.media_item_id == media_id
        ).delete(synchronize_session=False)
        self.session.delete(media_item)
        self.session.commit()
        return {
            "detail": "媒体项已删除",
            "watch_history_deleted": watch_history_deleted,
        }

    def clean_duplicate_numbers(self) -> dict:
        duplicate_numbers = (
            self.session.query(MediaItem.number)
            .filter(MediaItem.number.isnot(None), MediaItem.number != "")
            .group_by(MediaItem.number)
            .having(func.count(MediaItem.id) > 1)
            .all()
        )
        duplicate_count = 0
        watch_history_deleted = 0
        for (number,) in duplicate_numbers:
            items = (
                self.session.query(MediaItem)
                .filter(MediaItem.number == number)
                .order_by(desc(MediaItem.updatetime))
                .all()
            )
            for item in items[1:]:
                deleted_count = self.session.query(WatchHistory).filter(
                    WatchHistory.media_item_id == item.id
                ).delete(synchronize_session=False)
                watch_history_deleted += deleted_count
                self.session.delete(item)
                duplicate_count += 1
        self.session.commit()
        return {
            "detail": "媒体项已清理",
            "duplicate_number_deleted": duplicate_count,
            "watch_history_deleted": watch_history_deleted,
        }
