import types
import unittest

from src.ai import AIConfigurationError, AIProviderError, AIResponseError, DoubaoSeed16Service, normalize_markdown


def _build_completion(content):
    message = types.SimpleNamespace(content=content)
    choice = types.SimpleNamespace(message=message)
    return types.SimpleNamespace(choices=[choice])


class _FakeCompletions:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    def create(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._response


class _FakeChat:
    def __init__(self, response=None, error=None):
        self.completions = _FakeCompletions(response=response, error=error)


class _FakeClient:
    def __init__(self, response=None, error=None):
        self.chat = _FakeChat(response=response, error=error)


class DoubaoSeed16ServiceTests(unittest.TestCase):
    def test_generate_structured_json_success(self):
        service = DoubaoSeed16Service(
            client=_FakeClient(response=_build_completion('{"report_md":"# 标题\\n\\n- 一\\n- 二\\n- 三"}')),
            config={"model_id": "demo-model", "api_key": "demo-key", "base_url": "https://example.com"},
        )

        result = service.generate_structured_json(
            prompt="test",
            schema_name="demo",
            schema_description="demo schema",
            schema={"type": "object", "properties": {"report_md": {"type": "string"}}},
            strict=True,
        )

        self.assertEqual(result["report_md"], "# 标题\n\n- 一\n- 二\n- 三")

    def test_generate_structured_json_empty_response(self):
        service = DoubaoSeed16Service(
            client=_FakeClient(response=_build_completion("")),
            config={"model_id": "demo-model", "api_key": "demo-key"},
        )

        with self.assertRaises(AIResponseError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo",
                schema_description="demo schema",
                schema={"type": "object"},
            )

    def test_generate_structured_json_invalid_json(self):
        service = DoubaoSeed16Service(
            client=_FakeClient(response=_build_completion("not-json")),
            config={"model_id": "demo-model", "api_key": "demo-key"},
        )

        with self.assertRaises(AIResponseError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo",
                schema_description="demo schema",
                schema={"type": "object"},
            )

    def test_generate_structured_json_provider_error(self):
        service = DoubaoSeed16Service(
            client=_FakeClient(error=RuntimeError("boom")),
            config={"model_id": "demo-model", "api_key": "demo-key"},
        )

        with self.assertRaises(AIProviderError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo",
                schema_description="demo schema",
                schema={"type": "object"},
            )

    def test_missing_model_id_raises_configuration_error(self):
        service = DoubaoSeed16Service(
            client=_FakeClient(response=_build_completion('{"ok":true}')),
            config={"api_key": "demo-key"},
        )

        with self.assertRaises(AIConfigurationError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo",
                schema_description="demo schema",
                schema={"type": "object"},
            )

    def test_normalize_markdown(self):
        raw = "标题前文\n1. 第一项\n2. 第二项\n\n# 标题\n- 条目"
        expected = "标题前文\n\n1. 第一项\n\n2. 第二项\n\n# 标题\n\n- 条目"
        self.assertEqual(normalize_markdown(raw), expected)


if __name__ == "__main__":
    unittest.main()
