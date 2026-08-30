from sqlalchemy.orm import Session


def get_active_proxy(session: Session) -> dict:
    """获取系统代理设置，返回适合 requests 库使用的代理配置。"""
    from bonita.services.setting_service import SettingService
    return SettingService(session).get_proxy_for_requests()
