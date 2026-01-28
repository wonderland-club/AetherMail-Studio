import contextvars
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import REPO_ROOT, load_env, resolve_env_path

request_id_var = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def configure_logging(reset: Optional[bool] = None, force: bool = False) -> None:
    load_env()
    log_file = os.getenv("LOG_FILE", "logs/start_server.log")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_console = _to_bool(os.getenv("LOG_CONSOLE"), True)
    log_reset_on_start = _to_bool(os.getenv("LOG_RESET_ON_START"), True)
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "0") or 0)
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "3") or 3)

    if reset is None:
        reset = log_reset_on_start and os.getenv("APP_LOG_RESET_DONE") != "1"

    log_path = Path(resolve_env_path(log_file, REPO_ROOT))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if reset else "a"

    root = logging.getLogger()
    if root.handlers:
        if not force:
            return
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()

    root.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | request_id=%(request_id)s | %(message)s"
    )

    if max_bytes > 0:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            mode=mode,
            encoding="utf-8",
        )
    else:
        file_handler = logging.FileHandler(log_path, mode=mode, encoding="utf-8")

    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestIdFilter())
    root.addHandler(file_handler)

    if log_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.addFilter(RequestIdFilter())
        root.addHandler(console)

    logging.getLogger("werkzeug").setLevel(log_level)
