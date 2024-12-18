

import logging
from app.db import SessionFactory

logger = logging.getLogger(__name__)

def init_watcher():
    """
    initial watchdog
    """
    with SessionFactory() as session:
       
        logger.debug("watchdog initial")
