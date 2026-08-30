import logging
from bonita.modules.media_service.factory import init_media_servers
from bonita.modules.monitor.monitor import MonitorService

logger = logging.getLogger(__name__)


def init_monitor():
    """
    initial MonitorService
    """
    try:
        logger.info("initial MonitorService")
        MonitorService().start()
    except Exception as e:
        logger.error(e)


def stop_monitor():
    """
    stop MonitorService
    """
    MonitorService().stop()


def init_service():
    """
    initial Service
    """
    init_monitor()
    init_media_servers()
