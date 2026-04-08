"""Shared doubao-seed-1.8 client wrapper."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from src.config import get_doubao_seed_18_config

from .exceptions import AIConfigurationError, AIProviderError, AIResponseError

logger = logging.getLogger("ai.doubao_seed_18")


class DoubaoSeed18Service:
    """Thin service wrapper around the Ark Responses API for doubao-seed-1.8."""

    def __init__(self, client: Optional[Any] = None, config: Optional[Dict[str, Optional[str]]] = None) -> None:
        self._client = client
        self._config = config

    def _get_config(self) -> Dict[str, Optional[str]]:
        return dict(self._config or get_doubao_seed_18_config())

    def _get_model_id(self) -> str:
        model_id = (self._get_config().get("model_id") or "").strip()
        if not model_id:
            raise AIConfigurationError("AI 未启用：请在 .env 中配置 DOUBAO_SEED_18_MODEL_ID")
        return model_id

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        config = self._get_config()
        api_key = (config.get("api_key") or "").strip()
        if not api_key:
            raise AIConfigurationError("AI 未启用：请在 .env 中配置 DOUBAO_SEED_18_API_KEY")

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
    def _build_text_input(prompt: str) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    }
                ],
            }
        ]

    @staticmethod
    def _build_text_config(
        *,
        schema_name: str,
        schema_description: str,
        schema: Dict[str, Any],
        strict: bool,
    ) -> Dict[str, Any]:
        text_format: Dict[str, Any] = {
            "type": "json_schema",
            "name": schema_name,
            "schema": schema,
            "strict": strict,
        }
        if schema_description:
            text_format["description"] = schema_description
        return {"format": text_format}

    @staticmethod
    def _build_reasoning(reasoning_effort: Optional[str]) -> Optional[Dict[str, str]]:
        effort = (reasoning_effort or "").strip().lower()
        if not effort:
            return None
        return {"effort": effort}

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        outputs = getattr(response, "output", None) or []
        texts = []
        for output in outputs:
            if getattr(output, "type", None) != "message":
                continue
            for item in getattr(output, "content", None) or []:
                if getattr(item, "type", None) != "output_text":
                    continue
                text = getattr(item, "text", None)
                if text:
                    texts.append(text)
        return "\n".join(texts).strip()

    @staticmethod
    def _error_message_from_response(response: Any) -> str:
        error = getattr(response, "error", None)
        if error is None:
            return ""

        code = str(getattr(error, "code", "") or "").strip()
        message = str(getattr(error, "message", "") or "").strip()
        if code and message:
            return f"{code}: {message}"
        return code or message

    def create_response(
        self,
        *,
        input: Any,
        model_id: Optional[str] = None,
        instructions: Optional[str] = None,
        text: Optional[Dict[str, Any]] = None,
        reasoning_effort: str = "high",
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        client = self._get_client()
        resolved_model_id = (model_id or self._get_model_id()).strip()
        if not resolved_model_id:
            raise AIConfigurationError("AI 未启用：缺少可用的 model_id")

        request_payload: Dict[str, Any] = {
            "model": resolved_model_id,
            "input": input,
            "extra_headers": {"x-is-encrypted": "true"},
        }
        if instructions:
            request_payload["instructions"] = instructions
        if text is not None:
            request_payload["text"] = text
        if max_output_tokens is not None:
            request_payload["max_output_tokens"] = max_output_tokens
        if temperature is not None:
            request_payload["temperature"] = temperature
        if timeout is not None:
            request_payload["timeout"] = timeout

        reasoning = self._build_reasoning(reasoning_effort)
        if reasoning is not None:
            request_payload["reasoning"] = reasoning

        logger.info(
            "doubao_seed_18_request_begin | model_id=%s structured=%s",
            resolved_model_id,
            bool(text and text.get("format", {}).get("type") == "json_schema"),
        )
        try:
            response = client.responses.create(**request_payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("doubao_seed_18_request_failed | model_id=%s error=%s", resolved_model_id, exc)
            raise AIProviderError(f"AI 调用失败：{exc}") from exc

        error_message = self._error_message_from_response(response)
        if error_message:
            raise AIProviderError(f"AI 调用失败：{error_message}")

        status = str(getattr(response, "status", "") or "").strip().lower()
        if status == "failed":
            raise AIProviderError("AI 调用失败：response status=failed")
        if status == "incomplete":
            raise AIResponseError("AI 返回不完整")

        logger.info(
            "doubao_seed_18_request_ok | model_id=%s status=%s response_id=%s",
            resolved_model_id,
            status or "unknown",
            getattr(response, "id", ""),
        )
        return response

    def generate_text(
        self,
        *,
        prompt: Optional[str] = None,
        input: Any = None,
        model_id: Optional[str] = None,
        instructions: Optional[str] = None,
        reasoning_effort: str = "high",
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> str:
        request_input = input if input is not None else self._build_text_input(prompt or "")
        response = self.create_response(
            input=request_input,
            model_id=model_id,
            instructions=instructions,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        text = self._extract_response_text(response)
        if not text:
            raise AIResponseError("AI 返回为空")
        return text

    def generate_structured_json(
        self,
        *,
        schema_name: str,
        schema_description: str,
        schema: Dict[str, Any],
        prompt: Optional[str] = None,
        input: Any = None,
        model_id: Optional[str] = None,
        instructions: Optional[str] = None,
        reasoning_effort: str = "high",
        strict: bool = True,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        request_input = input if input is not None else self._build_text_input(prompt or "")
        response = self.create_response(
            input=request_input,
            model_id=model_id,
            instructions=instructions,
            text=self._build_text_config(
                schema_name=schema_name,
                schema_description=schema_description,
                schema=schema,
                strict=strict,
            ),
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            timeout=timeout,
        )

        text = self._extract_response_text(response)
        if not text:
            raise AIResponseError("AI 返回为空")

        try:
            data = json.loads(text)
        except Exception as exc:  # noqa: BLE001
            raise AIResponseError(f"AI 返回非 JSON：{exc}") from exc

        if not isinstance(data, dict):
            raise AIResponseError("AI 返回结构错误：根节点必须是对象")

        logger.info("doubao_seed_18_structured_json_ok | schema_name=%s keys=%s", schema_name, ",".join(sorted(data.keys())))
        return data
