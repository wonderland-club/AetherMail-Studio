"""Gunicorn configuration for production deployment."""

from __future__ import annotations

import multiprocessing
import os


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got: {raw_value}") from exc


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


cpu_count = multiprocessing.cpu_count() or 1
default_workers = max(2, min(4, cpu_count))

bind = os.getenv("GUNICORN_BIND", "127.0.0.1:5000")
workers = _env_int("GUNICORN_WORKERS", default_workers)
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = _env_int("GUNICORN_THREADS", 4)
timeout = _env_int("GUNICORN_TIMEOUT", 180)
graceful_timeout = _env_int("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _env_int("GUNICORN_KEEPALIVE", 5)
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
capture_output = _env_bool("GUNICORN_CAPTURE_OUTPUT", False)
proc_name = os.getenv("GUNICORN_PROC_NAME", "aethermail-studio")
preload_app = _env_bool("GUNICORN_PRELOAD", False)
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "127.0.0.1")

access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(D)s'
)
