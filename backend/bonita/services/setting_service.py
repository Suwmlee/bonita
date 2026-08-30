import logging
from urllib.parse import urljoin
from typing import Dict, Optional, Any, Tuple

import requests
from sqlalchemy.orm import Session

from bonita.db.models.setting import SystemSetting
from bonita.modules.media_service.emby import EmbyClient
from bonita.modules.downloader.transmission import TransmissionClient

logger = logging.getLogger(__name__)


class SettingService:
    """系统设置服务，提供对系统设置的业务逻辑操作"""

    def __init__(self, session: Session):
        self.session = session

    def get_setting(self, key: str, default: Any = None) -> str:
        """获取系统设置值

        Args:
            key: 设置键名
            default: 默认值，如果设置不存在

        Returns:
            str: 设置值
        """
        setting = self.session.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not setting:
            return default
        return setting.value

    def set_setting(self, key: str, value: str, description: Optional[str] = None) -> Dict:
        """设置系统设置值

        Args:
            key: 设置键名
            value: 设置值
            description: 设置描述

        Returns:
            Dict: 设置信息
        """
        setting = self.session.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not setting:
            setting = SystemSetting(key=key, value=value)
            if description:
                setting.description = description
            self.session.add(setting)
        else:
            setting.value = value
            if description:
                setting.description = description

        self.session.commit()
        return {
            "id": setting.id,
            "key": setting.key,
            "value": setting.value,
            "description": setting.description,
            "updatetime": setting.updatetime
        }

    def get_proxy_settings(self) -> Dict:
        """获取代理设置

        Returns:
            Dict: 代理设置字典
        """
        return {
            "enabled": self.get_setting("proxy_enabled", "false").lower() == "true",
            "http": self.get_setting("proxy_http", ""),
            "https": self.get_setting("proxy_https", "")
        }

    def get_emby_settings(self) -> Dict:
        """获取Emby媒体服务器设置

        Returns:
            Dict: Emby设置字典
        """
        return {
            "emby_host": self.get_setting("emby_host", ""),
            "emby_apikey": self.get_setting("emby_apikey", ""),
            "emby_user": self.get_setting("emby_user", ""),
            "enabled": self.get_setting("emby_enabled", "false").lower() == "true"
        }

    def get_jellyfin_settings(self) -> Dict:
        """获取Jellyfin媒体服务器设置

        Returns:
            Dict: Jellyfin设置字典
        """
        return {
            "jellyfin_host": self.get_setting("jellyfin_host", ""),
            "jellyfin_apikey": self.get_setting("jellyfin_apikey", ""),
            "enabled": self.get_setting("jellyfin_enabled", "false").lower() == "true"
        }

    def get_transmission_settings(self) -> Dict:
        """获取Transmission下载器设置

        Returns:
            Dict: Transmission设置字典
        """
        return {
            "transmission_host": self.get_setting("transmission_host", ""),
            "transmission_username": self.get_setting("transmission_username", ""),
            "transmission_password": self.get_setting("transmission_password", ""),
            "transmission_source_path": self.get_setting("transmission_source_path", ""),
            "transmission_dest_path": self.get_setting("transmission_dest_path", ""),
            "enabled": self.get_setting("transmission_enabled", "false").lower() == "true"
        }

    def update_proxy_settings(self, enabled: bool, http: Optional[str] = None,
                              https: Optional[str] = None) -> None:
        """更新代理设置

        Args:
            enabled: 是否启用代理
            http: HTTP代理地址
            https: HTTPS代理地址
        """
        self.set_setting(
            "proxy_enabled",
            str(enabled).lower(),
            "是否启用代理"
        )

        if http is not None:
            self.set_setting(
                "proxy_http",
                http,
                "HTTP代理地址"
            )

        if https is not None:
            self.set_setting(
                "proxy_https",
                https,
                "HTTPS代理地址"
            )

    def update_emby_settings(self, host: str, apikey: str, user: str,
                             enabled: bool) -> Tuple[bool, str]:
        """更新Emby媒体服务器设置

        Args:
            host: Emby服务器地址
            apikey: Emby API密钥
            user: Emby用户名
            enabled: 是否启用Emby

        Returns:
            Tuple[bool, str]: 成功状态和消息
        """
        self.set_setting(
            "emby_host",
            host,
            "Emby服务器地址"
        )

        self.set_setting(
            "emby_apikey",
            apikey,
            "Emby API密钥"
        )

        self.set_setting(
            "emby_user",
            user,
            "Emby用户名"
        )

        self.set_setting(
            "emby_enabled",
            str(enabled).lower(),
            "是否启用Emby"
        )

        return True, "Emby设置已更新"

    def update_jellyfin_settings(self, host: str, apikey: str, enabled: bool) -> None:
        """更新Jellyfin媒体服务器设置

        Args:
            host: Jellyfin服务器地址
            apikey: Jellyfin API密钥
            enabled: 是否启用Jellyfin
        """
        self.set_setting(
            "jellyfin_enabled",
            str(enabled).lower(),
            "是否启用Jellyfin"
        )

        self.set_setting(
            "jellyfin_host",
            host,
            "Jellyfin服务器地址"
        )

        self.set_setting(
            "jellyfin_apikey",
            apikey,
            "Jellyfin API密钥"
        )

    def update_transmission_settings(self, host: str, username: str, password: str,
                                     source_path: str, dest_path: str,
                                     enabled: bool) -> None:
        """更新Transmission下载器设置

        Args:
            host: Transmission服务器地址  
            username: Transmission用户名
            password: Transmission密码
            source_path: Transmission路径映射-容器内路径
            dest_path: Transmission路径映射-宿主机路径
            enabled: 是否启用Transmission
        """
        self.set_setting(
            "transmission_enabled",
            str(enabled).lower(),
            "是否启用Transmission下载器"
        )

        self.set_setting(
            "transmission_host",
            host,
            "Transmission服务器地址"
        )

        self.set_setting(
            "transmission_username",
            username,
            "Transmission用户名"
        )

        self.set_setting(
            "transmission_password",
            password,
            "Transmission密码"
        )

        self.set_setting(
            "transmission_source_path",
            source_path,
            "Transmission路径映射-容器内路径"
        )

        self.set_setting(
            "transmission_dest_path",
            dest_path,
            "Transmission路径映射-宿主机路径"
        )

    def get_proxy_for_requests(self) -> Optional[Dict[str, str]]:
        """返回适合 requests 库使用的代理配置；未启用时返回 None。"""
        rows = self.session.query(SystemSetting).filter(
            SystemSetting.key.in_(["proxy_enabled", "proxy_http", "proxy_https"])
        ).all()
        proxy_dict = {setting.key: setting.value for setting in rows}
        if proxy_dict.get("proxy_enabled", "false").lower() != "true":
            return None
        proxy = {}
        if proxy_dict.get("proxy_http"):
            proxy["http"] = proxy_dict["proxy_http"]
        if proxy_dict.get("proxy_https"):
            proxy["https"] = proxy_dict["proxy_https"]
        return proxy or None

    def try_initialize_emby(
        self,
        host: Optional[str] = None,
        apikey: Optional[str] = None,
        user: Optional[str] = None,
    ) -> bool:
        """用给定参数或当前设置初始化 Emby 客户端。"""
        if host is None or apikey is None or user is None:
            current = self.get_emby_settings()
            if not current.get("enabled"):
                return False
            host = current.get("emby_host") or ""
            apikey = current.get("emby_apikey") or ""
            user = current.get("emby_user") or ""
        if not host or not apikey or not user:
            return False
        return bool(EmbyClient().initialize(host, apikey, user))

    def save_emby_settings(
        self, host: str, apikey: str, user: str, enabled: bool
    ) -> Tuple[bool, str]:
        """保存 Emby 设置；启用时先验证连接。"""
        if enabled:
            if not self.try_initialize_emby(host, apikey, user):
                return False, "Emby设置已保存但初始化失败，请检查设置是否正确"
        self.update_emby_settings(host=host, apikey=apikey, user=user, enabled=enabled)
        return True, "Emby设置已更新"

    def test_emby_connection(self, host: str, apikey: str, user: str) -> Tuple[bool, str]:
        try:
            if EmbyClient().initialize(host, apikey, user):
                return True, "Emby连接成功，API Key有效"
            return False, "Emby连接失败，请检查服务器地址、API Key和用户名"
        except Exception as e:
            logger.exception("测试Emby连接时出错")
            return False, f"测试Emby连接时出错: {str(e)}"

    def test_jellyfin_connection(self, host: str, apikey: str) -> Tuple[bool, str]:
        try:
            base_url = (host or "").rstrip("/")
            api_url = urljoin(f"{base_url}/", "System/Info")
            headers = {"X-Emby-Token": apikey}
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return True, "Jellyfin连接成功，API Key有效"
            return False, f"Jellyfin连接失败，状态码: {response.status_code}"
        except requests.RequestException as e:
            return False, f"Jellyfin连接失败: {str(e)}"
        except Exception as e:
            logger.exception("测试Jellyfin连接时出错")
            return False, f"测试Jellyfin连接时出错: {str(e)}"

    def test_transmission_connection(
        self,
        host: str,
        username: str,
        password: str,
        source_path: str = "",
        dest_path: str = "",
    ) -> Tuple[bool, str]:
        try:
            init_success = TransmissionClient().initialize(
                url=host,
                username=username,
                password=password,
                source_path=source_path,
                dest_path=dest_path,
            )
            if init_success:
                return True, "Transmission连接成功"
            return False, "Transmission连接失败，请检查服务器地址、用户名和密码"
        except Exception as e:
            logger.exception("测试Transmission连接时出错")
            return False, f"测试Transmission连接时出错: {str(e)}"
