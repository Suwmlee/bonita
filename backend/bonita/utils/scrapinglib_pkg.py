import logging
import os
import subprocess
import sys
import importlib
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PACKAGE_NAME = "scrapinglib"
PYPI_JSON_URL = "https://pypi.org/pypi/scrapinglib/json"


def extra_site_packages_dir() -> str:
    """可写的第三方包目录，用于容器内非 root 用户升级依赖。"""
    config_dir = "/config"
    if os.path.isdir(config_dir) and os.access(config_dir, os.W_OK):
        path = os.path.join(config_dir, "python-packages")
    else:
        data_dir = os.path.abspath("./data")
        os.makedirs(data_dir, exist_ok=True)
        path = os.path.join(data_dir, "python-packages")
    os.makedirs(path, exist_ok=True)
    return path


def ensure_extra_site_packages() -> str:
    """把额外包目录插到 sys.path 最前，保证升级后的包优先生效。"""
    path = extra_site_packages_dir()
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)
    return path


def get_installed_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "0"


def _parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in value.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(latest: str, current: str) -> bool:
    try:
        return _parse_version(latest) > _parse_version(current)
    except Exception:
        return latest != current


def fetch_latest_version(proxy: Optional[dict] = None) -> str:
    response = requests.get(PYPI_JSON_URL, timeout=15, proxies=proxy or {})
    response.raise_for_status()
    return response.json()["info"]["version"]


def reload_modules() -> None:
    importlib.invalidate_caches()
    names = [
        name
        for name in list(sys.modules)
        if name == PACKAGE_NAME or name.startswith(f"{PACKAGE_NAME}.")
    ]
    for name in names:
        del sys.modules[name]
    __import__(PACKAGE_NAME)


def _run_pip(args: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pip", *args],
        capture_output=True,
        text=True,
    )
    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode == 0:
        return True, output
    logger.warning("pip install scrapinglib failed: %s", output)
    return False, output


def pip_install_upgrade() -> tuple[bool, str]:
    """升级 scrapinglib。优先写入系统 site-packages，失败则装到可写目录。"""
    ok, output = _run_pip(
        ["install", "--upgrade", "--disable-pip-version-check", PACKAGE_NAME]
    )
    if ok:
        return True, output

    target = ensure_extra_site_packages()
    ok, target_output = _run_pip(
        [
            "install",
            "--upgrade",
            "--disable-pip-version-check",
            "--target",
            target,
            PACKAGE_NAME,
        ]
    )
    if ok:
        return True, target_output
    return False, target_output or output
