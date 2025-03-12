

import logging
from bonita.db import SessionFactory
from bonita.db.models.task import TransferConfig
from bonita.modules.monitor.monitor import MonitorService

logger = logging.getLogger(__name__)


def init_monitor():
    """
    initial MonitorService
    """
    try:
        logger.info("MonitorService initial")
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
