from sqlalchemy.orm import Session
from bonita.db.models.setting import SystemSetting
from typing import List, Dict, Optional, Any, Union, Tuple


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
