"""同步批提交上下文：父剧缓存、路径缓存、攒批 flush。"""

from contextlib import contextmanager
from contextvars import ContextVar

from bonita.modules.media_service.client import RemoteItem

_SYNC_BATCH = 200
_sync_ctx: ContextVar = ContextVar("bonita_media_sync", default=None)


def is_blank(value) -> bool:
    return value is None or str(value).strip() == ""


def current_sync():
    return _sync_ctx.get()


@contextmanager
def use_sync_context(ctx):
    token = _sync_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _sync_ctx.reset(token)


@contextmanager
def sync_scope(session):
    """一次同步共用父剧字典、路径缓存和攒批提交。已在同步里时沿用外层。"""
    current = current_sync()
    if current is not None:
        yield current
        return
    ctx = SyncContext()
    with use_sync_context(ctx):
        try:
            yield ctx
        finally:
            ctx.finish(session)


class SyncContext:
    def __init__(self):
        self.series_by_id = {}
        self.series_fetched = set()
        self.exact_records = {}
        self.path_records = {}
        self.library_index = None
        self.index_ready = False
        self.dest_paths_by_number = None
        self.media_by_id = None
        self._pending = 0
        self._touched = False

    def mark_touched(self):
        self._touched = True

    def _needs_commit(self, session):
        return self._touched or bool(session.new or session.dirty or session.deleted)

    def _commit(self, session):
        if not self._needs_commit(session):
            return
        session.commit()
        self.exact_records.clear()
        self.path_records.clear()
        self._touched = False

    def tick(self, session):
        self._pending += 1
        if self._pending < _SYNC_BATCH:
            return
        self._pending = 0
        self._commit(session)

    def finish(self, session):
        self._commit(session)
        self._pending = 0

    def note_committed(self):
        self._pending = 0
        self._touched = False
        self.exact_records.clear()
        self.path_records.clear()

    def remember_series(self, item: RemoteItem):
        if not item or not item.remote_id:
            return
        prev = self.series_by_id.get(item.remote_id)
        if prev is None or prev is item:
            self.series_by_id[item.remote_id] = item
            return
        if is_blank(prev.original_title) and not is_blank(item.original_title):
            prev.original_title = item.original_title
        if is_blank(prev.title) and item.title:
            prev.title = item.title
        for key in ("imdb", "tmdb", "tvdb"):
            if is_blank(prev.provider_ids.get(key)) and not is_blank(item.provider_ids.get(key)):
                prev.provider_ids[key] = item.provider_ids[key]

    def load_series(self, client, remote_id):
        if not remote_id:
            return None
        cached = self.series_by_id.get(remote_id)
        if remote_id in self.series_fetched or _series_remote_complete(cached):
            return cached
        details = client.get_item(remote_id)
        self.series_fetched.add(remote_id)
        if details:
            self.remember_series(details)
        return self.series_by_id.get(remote_id)


def _series_remote_complete(item: RemoteItem) -> bool:
    return bool(
        item
        and not is_blank(item.imdb_id)
        and not is_blank(item.tmdb_id)
        and not is_blank(item.tvdb_id)
        and not is_blank(item.original_title)
    )


def commit_or_flush(session):
    ctx = current_sync()
    if ctx is not None:
        session.flush()
        ctx.mark_touched()
        return
    session.commit()


def save_new(session, obj):
    ctx = current_sync()
    if ctx is not None:
        session.add(obj)
        session.flush()
        ctx.mark_touched()
        return
    obj.create(session)


def series_item(client, remote_id):
    if not remote_id:
        return None
    ctx = current_sync()
    if ctx is None:
        return client.get_item(remote_id)
    return ctx.load_series(client, remote_id)
