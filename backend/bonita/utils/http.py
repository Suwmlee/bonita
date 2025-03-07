from sqlalchemy.orm import Session

from bonita.db.models.setting import SystemSetting


def get_active_proxy(session: Session) -> dict:
    """获取系统代理设置

    检索系统代理设置并返回适合 requests 库使用的代理配置

    Args:
        session: 数据库会话

    Returns:
        dict: 代理设置字典，格式为 {"http": "http://proxy.com:8080", "https": "http://proxy.com:8080"}
              如果代理未启用，则返回 None
    """
    # 一次性获取所有代理相关设置以减少数据库查询
    proxy_settings = session.query(SystemSetting).filter(
        SystemSetting.key.in_(["proxy_enabled", "proxy_http", "proxy_https"])
    ).all()

    # 将查询结果转换为字典
    proxy_dict = {setting.key: setting.value for setting in proxy_settings}

    # 检查代理是否启用
    proxy_enabled = proxy_dict.get("proxy_enabled", "false").lower() == "true"

    if not proxy_enabled:
        return None

    # 构建代理配置
    proxy = {}
    proxy_http = proxy_dict.get("proxy_http")
    proxy_https = proxy_dict.get("proxy_https")

    if proxy_http:
        proxy["http"] = proxy_http
    if proxy_https:
        proxy["https"] = proxy_https

    # 如果没有配置任何代理服务器，也返回None
    return proxy if proxy else None
