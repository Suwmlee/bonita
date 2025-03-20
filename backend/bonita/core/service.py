

import logging
from bonita.db import SessionFactory
from bonita.db.models.setting import SystemSetting
from bonita.db.models.task import TransferConfig
from bonita.modules.media_service.emby import EmbyService
from bonita.modules.monitor.monitor import MonitorService

logger = logging.getLogger(__name__)


def init_monitor():
    """
    initial MonitorService
    """
    try:
        logger.info("initial MonitorService")
        MonitorService().start()
        with SessionFactory() as session:
            task_configs = session.query(TransferConfig).all()
            # 为每个启用了自动监控的任务添加目录监控
            for task_config in task_configs:
                if task_config.auto_watch:
                    MonitorService().start_monitoring_directory(task_config.source_folder, task_config.id)
    except Exception as e:
        logger.error(e)


def stop_monitor():
    """
    stop MonitorService
    """
    MonitorService().stop()


def init_emby():
    """
    initial EmbyService
    """
    with SessionFactory() as session:
        logger.info("initial EmbyService")
        emby_enabled = session.query(SystemSetting).filter(SystemSetting.key == "emby_enabled").first()
        if not emby_enabled or emby_enabled.value != "true":
            logger.info("Emby is not enabled")
            return
        emby_host = session.query(SystemSetting).filter(SystemSetting.key == "emby_host").first()
        emby_apikey = session.query(SystemSetting).filter(SystemSetting.key == "emby_apikey").first()
        emby_user = session.query(SystemSetting).filter(SystemSetting.key == "emby_user").first()
        if not emby_host or not emby_apikey or not emby_user:
            logger.info("Emby host or API key or user not configured")
            return
        EmbyService().initialize(emby_host.value, emby_apikey.value, emby_user.value)


def init_service():
    """
    initial Service
    """
    init_monitor()
    init_emby()
