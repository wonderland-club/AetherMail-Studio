"""Feishu custom bot client."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from urllib import request
from urllib.error import HTTPError, URLError

from src.config import get_feishu_bot_config


class FeishuBotConfigError(Exception):
    """Raised when Feishu bot configuration is missing or invalid."""


class FeishuBotRequestError(Exception):
    """Raised when Feishu bot request fails."""


@dataclass(frozen=True)
class FeishuBotResult:
    """Feishu bot request result."""

    ok: bool
    status_code: int
    response_text: str


class FeishuBotClient:
    """Thin client for Feishu custom bot webhooks."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: Optional[float] = None,
        opener: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._secret = secret
        self._timeout = timeout
        self._opener = opener or request.urlopen

    def _get_config(self) -> Dict[str, Optional[str]]:
        return dict(get_feishu_bot_config())

    def _get_webhook_url(self) -> str:
        if self._webhook_url is not None:
            webhook_url = self._webhook_url.strip()
        else:
            webhook_url = (self._get_config().get("webhook_url") or "").strip()
        if not webhook_url:
            raise FeishuBotConfigError("飞书机器人未启用：请在 .env 中配置 FEISHU_BOT_WEBHOOK_URL")
        return webhook_url

    def _get_secret(self) -> str:
        if self._secret is not None:
            return self._secret.strip()
        return (self._get_config().get("secret") or "").strip()

    def _get_timeout(self) -> float:
        if self._timeout is not None:
            return float(self._timeout)

        timeout_raw = (self._get_config().get("timeout_seconds") or "").strip()
        if not timeout_raw:
            return 10.0

        try:
            return float(timeout_raw)
        except ValueError as exc:
            raise FeishuBotConfigError("FEISHU_BOT_TIMEOUT_SECONDS 配置无效") from exc

    @staticmethod
    def build_sign(timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _build_payload(self, text: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "msg_type": "text",
            "content": {
                "text": text,
            },
        }

        secret = self._get_secret()
        if secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self.build_sign(timestamp, secret)

        return payload

    @staticmethod
    def _validate_response(status_code: int, response_text: str) -> None:
        if status_code >= 400:
            raise FeishuBotRequestError(f"飞书机器人请求失败：HTTP {status_code}")

        if not response_text:
            return

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return

        if not isinstance(data, dict):
            return

        code = data.get("code", data.get("StatusCode"))
        if code in (None, 0):
            return

        message = data.get("msg", data.get("StatusMessage")) or "unknown error"
        raise FeishuBotRequestError(f"飞书机器人请求失败：{message}")

    def send_text(self, text: str) -> FeishuBotResult:
        webhook_url = self._get_webhook_url()
        payload = self._build_payload(text)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with self._opener(req, timeout=self._get_timeout()) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                response_text = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
            raise FeishuBotRequestError(f"飞书机器人请求失败：HTTP {exc.code} {response_text}") from exc
        except URLError as exc:
            raise FeishuBotRequestError(f"飞书机器人请求失败：{exc}") from exc

        self._validate_response(status_code, response_text)
        return FeishuBotResult(ok=True, status_code=int(status_code), response_text=response_text)
