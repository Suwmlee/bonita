

import logging
from bonita.db import SessionFactory
from bonita.db.models.task import TransferConfig
from bonita.watcher.manager import watcher_manager

logger = logging.getLogger(__name__)


def init_watcher():
    """
    initial watchdog
    """
    try:
        session = SessionFactory()
        logger.info("watchdog initial")
        task_configs = session.query(TransferConfig).all()
        # 为每个启用了自动监控的任务添加目录监控
        for task_config in task_configs:
            if task_config.auto_watch:
                logger.info(f"add watcher for task config: {task_config.id}")
                watcher_manager.add_directory(task_config.source_folder, task_config.id)
    except Exception as e:
        logger.error(e)
    finally:
        session.close()


def stop_watcher():
    """
    stop watchdog
    """
    watcher_manager.stop()
