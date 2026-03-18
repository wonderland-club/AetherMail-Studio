import unittest

import app as app_module
from src.ai import AIConfigurationError, AIResponseError
from src.core.renderer import Renderer


class AIAPITests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_templates_include_doubao_smoke_test(self):
        response = self.client.get("/templates")
        self.assertEqual(response.status_code, 200)
        template_ids = {item["id"] for item in response.get_json()["templates"]}
        self.assertIn("doubao_smoke_test", template_ids)

    def test_doubao_smoke_test_requires_topic(self):
        response = self.client.post(
            "/api/send",
            json={
                "template": "doubao_smoke_test",
                "to": "user@example.com",
                "data": {},
            },
        )
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["missing_fields"], ["TOPIC"])

    def test_ai_configuration_error_maps_to_500(self):
        definition = app_module.template_registry.get("doubao_smoke_test")
        original = definition.render_callable

        def _boom(data, renderer):
            raise AIConfigurationError("missing config")

        definition.render_callable = _boom
        try:
            response = self.client.post(
                "/api/send",
                json={
                    "template": "doubao_smoke_test",
                    "to": "user@example.com",
                    "data": {"TOPIC": "demo"},
                },
            )
        finally:
            definition.render_callable = original

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"], "missing config")

    def test_ai_response_error_maps_to_502(self):
        definition = app_module.template_registry.get("doubao_smoke_test")
        original = definition.render_callable

        def _boom(data, renderer):
            raise AIResponseError("bad response")

        definition.render_callable = _boom
        try:
            response = self.client.post(
                "/api/send",
                json={
                    "template": "doubao_smoke_test",
                    "to": "user@example.com",
                    "data": {"TOPIC": "demo"},
                },
            )
        finally:
            definition.render_callable = original

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"], "bad response")

    def test_protein_template_can_render_with_stubbed_ai_service(self):
        definition = app_module.template_registry.get("protein_calculation")
        globals_dict = definition.render_callable.__globals__
        original_service = globals_dict["DoubaoService"]

        class _FakeService:
            def generate_structured_json(self, **kwargs):
                return {"report_md": "# AI 报告\n\n- 第一条\n- 第二条\n- 第三条"}

        globals_dict["DoubaoService"] = _FakeService
        try:
            markdown = definition.render(
                {
                    "name": "测试用户",
                    "height_cm": 168,
                    "weight_kg": 62,
                    "age": 32,
                    "sex": "female",
                    "activity_level": "moderate",
                    "goal": "maintain",
                    "kidney_status": "none",
                    "diet_type": "omnivore",
                    "female_stage": "none",
                },
                Renderer(),
            )
        finally:
            globals_dict["DoubaoService"] = original_service

        self.assertIn("# 写给测试用户：你的蛋白质摄入建议", markdown)
        self.assertIn("# AI 报告", markdown)


if __name__ == "__main__":
    unittest.main()
