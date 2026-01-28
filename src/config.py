"""
邮件发送系统配置文件
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_LOADED = False


def resolve_env_path(value: str, base_dir: Optional[Path] = None) -> str:
    if not value:
        return ""
    base_dir = base_dir or REPO_ROOT
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return str(path)


def _apply_ssl_cert_file() -> None:
    ssl_file = os.getenv("SSL_CERT_FILE")
    if ssl_file:
        os.environ["SSL_CERT_FILE"] = resolve_env_path(ssl_file, REPO_ROOT)
        return
    try:
        import certifi
    except Exception:
        return
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())


def load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(REPO_ROOT / ".env")
    _ENV_LOADED = True
    _apply_ssl_cert_file()


def get_service_config(service: str, defaults: Optional[Dict[str, Optional[str]]] = None) -> Dict[str, Optional[str]]:
    load_env()
    defaults = defaults or {}
    service = service.upper()
    config: Dict[str, Optional[str]] = {}
    for key, default in defaults.items():
        env_key = f"{service}_{key.upper()}"
        config[key] = os.getenv(env_key, default)
    return config


def get_doubao_config() -> Dict[str, Optional[str]]:
    defaults = {
        "api_key": None,
        "model_id": None,
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    }
    config = get_service_config("DOUBAO", defaults)
    legacy = get_service_config("ARK", defaults)
    for key, value in legacy.items():
        if not config.get(key) and value:
            config[key] = value
    return config


def validate_smtp_config() -> None:
    missing = []
    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if missing:
        raise ValueError(f"请在.env文件中配置: {', '.join(missing)}")


load_env()

# SMTP配置
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# 邮件配置（不提供默认值，需在环境变量中显式设置）
DEFAULT_SENDER_NAME = os.getenv("DEFAULT_SENDER_NAME")
DEFAULT_SUBJECT_PREFIX = os.getenv("DEFAULT_SUBJECT_PREFIX")
