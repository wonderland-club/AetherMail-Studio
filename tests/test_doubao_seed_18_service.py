import types
import unittest

from src.ai import AIConfigurationError, AIProviderError, AIResponseError, DoubaoSeed18Service


def _build_response(text="", *, status="completed", error=None):
    output_text = types.SimpleNamespace(type="output_text", text=text)
    message = types.SimpleNamespace(type="message", content=[output_text])
    return types.SimpleNamespace(
        id="resp_demo",
        status=status,
        error=error,
        output=[message],
    )


class _FakeResponses:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return self._response


class _FakeClient:
    def __init__(self, response=None, error=None):
        self.responses = _FakeResponses(response=response, error=error)


class DoubaoSeed18ServiceTests(unittest.TestCase):
    def test_generate_structured_json_success(self):
        client = _FakeClient(response=_build_response('{"report_md":"# 标题\\n\\n- 一\\n- 二"}'))
        service = DoubaoSeed18Service(
            client=client,
            config={"model_id": "ep-demo", "api_key": "demo-key", "base_url": "https://example.com/api/v3"},
        )

        result = service.generate_structured_json(
            prompt="test prompt",
            schema_name="demo_schema",
            schema_description="demo schema",
            schema={"type": "object", "properties": {"report_md": {"type": "string"}}},
        )

        self.assertEqual(result["report_md"], "# 标题\n\n- 一\n- 二")
        self.assertEqual(client.responses.last_kwargs["model"], "ep-demo")
        self.assertEqual(client.responses.last_kwargs["input"][0]["content"][0]["type"], "input_text")
        self.assertEqual(client.responses.last_kwargs["text"]["format"]["type"], "json_schema")
        self.assertTrue(client.responses.last_kwargs["text"]["format"]["strict"])
        self.assertEqual(client.responses.last_kwargs["reasoning"], {"effort": "high"})

    def test_generate_structured_json_supports_multimodal_input(self):
        client = _FakeClient(response=_build_response('{"answer":"图片里有一只猫"}'))
        service = DoubaoSeed18Service(
            client=client,
            config={"model_id": "ep-demo", "api_key": "demo-key"},
        )
        input_payload = [
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": "https://example.com/cat.png"},
                    {"type": "input_text", "text": "你看见了什么？"},
                ],
            }
        ]

        result = service.generate_structured_json(
            input=input_payload,
            schema_name="vision_schema",
            schema_description="vision schema",
            schema={"type": "object", "properties": {"answer": {"type": "string"}}},
        )

        self.assertEqual(result["answer"], "图片里有一只猫")
        self.assertEqual(client.responses.last_kwargs["input"], input_payload)

    def test_generate_text_success(self):
        service = DoubaoSeed18Service(
            client=_FakeClient(response=_build_response("你好，世界")),
            config={"model_id": "ep-demo", "api_key": "demo-key"},
        )

        text = service.generate_text(prompt="say hi")

        self.assertEqual(text, "你好，世界")

    def test_generate_structured_json_invalid_json(self):
        service = DoubaoSeed18Service(
            client=_FakeClient(response=_build_response("not-json")),
            config={"model_id": "ep-demo", "api_key": "demo-key"},
        )

        with self.assertRaises(AIResponseError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo_schema",
                schema_description="demo schema",
                schema={"type": "object"},
            )

    def test_incomplete_response_raises_error(self):
        service = DoubaoSeed18Service(
            client=_FakeClient(response=_build_response("{}", status="incomplete")),
            config={"model_id": "ep-demo", "api_key": "demo-key"},
        )

        with self.assertRaises(AIResponseError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo_schema",
                schema_description="demo schema",
                schema={"type": "object"},
            )

    def test_provider_error_raises_error(self):
        service = DoubaoSeed18Service(
            client=_FakeClient(error=RuntimeError("boom")),
            config={"model_id": "ep-demo", "api_key": "demo-key"},
        )

        with self.assertRaises(AIProviderError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo_schema",
                schema_description="demo schema",
                schema={"type": "object"},
            )

    def test_missing_model_id_raises_configuration_error(self):
        service = DoubaoSeed18Service(
            client=_FakeClient(response=_build_response("{}")),
            config={"api_key": "demo-key"},
        )

        with self.assertRaises(AIConfigurationError):
            service.generate_structured_json(
                prompt="test",
                schema_name="demo_schema",
                schema_description="demo schema",
                schema={"type": "object"},
            )


if __name__ == "__main__":
    unittest.main()
