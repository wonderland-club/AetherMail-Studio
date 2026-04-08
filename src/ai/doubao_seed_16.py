"""Shared doubao-seed-1.6 client wrapper."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from src.config import get_doubao_seed_16_config

from .exceptions import AIConfigurationError, AIProviderError, AIResponseError

logger = logging.getLogger("ai.doubao_seed_16")


class DoubaoSeed16Service:
    """Thin service wrapper around the Ark chat completion API for doubao-seed-1.6."""

    def __init__(self, client: Optional[Any] = None, config: Optional[Dict[str, Optional[str]]] = None) -> None:
        self._client = client
        self._config = config

    def _get_config(self) -> Dict[str, Optional[str]]:
        return dict(self._config or get_doubao_seed_16_config())

    def _get_model_id(self) -> str:
        model_id = (self._get_config().get("model_id") or "").strip()
        if not model_id:
            raise AIConfigurationError("AI 未启用：请在 .env 中配置 DOUBAO_SEED_16_MODEL_ID")
        return model_id

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        config = self._get_config()
        api_key = (config.get("api_key") or "").strip()
        if not api_key:
            raise AIConfigurationError("AI 未启用：请在 .env 中配置 DOUBAO_SEED_16_API_KEY")

        try:
            from volcenginesdkarkruntime import Ark
        except Exception as exc:  # noqa: BLE001
            raise AIConfigurationError(
                "AI 未启用：请安装 volcenginesdkarkruntime 或确认 volcengine-python-sdk[ark] 已正确安装"
            ) from exc

        base_url = (config.get("base_url") or "https://ark.cn-beijing.volces.com/api/v3").strip()
        self._client = Ark(base_url=base_url, api_key=api_key)
        return self._client

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text") or "")
            return "\n".join(texts)
        return str(content)

    def generate_structured_json(
        self,
        *,
        prompt: str,
        schema_name: str,
        schema_description: str,
        schema: Dict[str, Any],
        reasoning_effort: str = "high",
        strict: bool = False,
    ) -> Dict[str, Any]:
        client = self._get_client()
        model_id = self._get_model_id()
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "description": schema_description,
                "schema": schema,
                "strict": strict,
            },
        }

        logger.info("doubao_seed_16_request_begin | model_id=%s schema_name=%s", model_id, schema_name)
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
                response_format=response_format,
                reasoning_effort=reasoning_effort,
                extra_headers={"x-is-encrypted": "true"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("doubao_seed_16_request_failed | schema_name=%s error=%s", schema_name, exc)
            raise AIProviderError(f"AI 调用失败：{exc}") from exc

        message = completion.choices[0].message if getattr(completion, "choices", None) else None
        text = self._content_to_text(getattr(message, "content", None))
        if not text:
            raise AIResponseError("AI 返回为空")

        try:
            data = json.loads(text)
        except Exception as exc:  # noqa: BLE001
            raise AIResponseError(f"AI 返回非 JSON：{exc}") from exc

        if not isinstance(data, dict):
            raise AIResponseError("AI 返回结构错误：根节点必须是对象")

        logger.info("doubao_seed_16_request_ok | schema_name=%s keys=%s", schema_name, ",".join(sorted(data.keys())))
        return data
