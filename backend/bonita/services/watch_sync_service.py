from typing import Any, Optional

from sqlalchemy.orm import Session

from bonita.modules.media_service.client import SOURCE_EMBY
from bonita.modules.media_service.watch import sync_watch_history
from bonita.modules.media_service.webhook import handle_webhook_event


class WatchSyncService:
    """观看记录同步与媒体服务器 webhook 处理。"""

    def __init__(self, session: Session):
        self.session = session

    def sync_history(self, direction: str = "from_server", force: bool = False, source: str = SOURCE_EMBY) -> None:
        sync_watch_history(self.session, direction=direction, force=force, source=source)

    def handle_webhook(self, payload: dict[str, Any], source: str = SOURCE_EMBY) -> Optional[str]:
        return handle_webhook_event(self.session, payload, source=source)
