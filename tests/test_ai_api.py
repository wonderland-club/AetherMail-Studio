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

    def test_doubao_smoke_test_can_render_with_stubbed_doubao_seed_16_service(self):
        definition = app_module.template_registry.get("doubao_smoke_test")
        globals_dict = definition.render_callable.__globals__
        original_service = globals_dict["DoubaoSeed16Service"]

        class _FakeService:
            def generate_structured_json(self, **kwargs):
                return {"report_md": "# Smoke Test\n\n这是一段摘要。\n\n- 第一条\n- 第二条\n- 第三条"}

        globals_dict["DoubaoSeed16Service"] = _FakeService
        try:
            markdown = definition.render(
                {"NAME": "测试用户", "TOPIC": "新 doubao-seed-1.6 接口验证"},
                Renderer(),
            )
        finally:
            globals_dict["DoubaoSeed16Service"] = original_service

        self.assertIn("# Smoke Test", markdown)
        self.assertIn("测试用户", markdown)

    def test_protein_template_can_render_with_stubbed_ai_service(self):
        definition = app_module.template_registry.get("protein_calculation")
        globals_dict = definition.render_callable.__globals__
        original_service = globals_dict["DoubaoSeed16Service"]
        original_feishu = globals_dict["FeishuBotClient"]
        sent_messages = []

        class _FakeService:
            def generate_structured_json(self, **kwargs):
                return {"report_md": "# AI 报告\n\n- 第一条\n- 第二条\n- 第三条"}

        class _FakeFeishuBotClient:
            def send_text(self, text):
                sent_messages.append(text)

        globals_dict["DoubaoSeed16Service"] = _FakeService
        globals_dict["FeishuBotClient"] = _FakeFeishuBotClient
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
            globals_dict["DoubaoSeed16Service"] = original_service
            globals_dict["FeishuBotClient"] = original_feishu

        self.assertIn("# AI 报告", markdown)
        self.assertNotIn("你的蛋白质摄入建议", markdown)
        self.assertEqual(len(sent_messages), 1)
        self.assertIn("蛋白质模板执行成功", sent_messages[0])
        self.assertIn("用户昵称：测试用户", sent_messages[0])
        self.assertIn("关键信息：", sent_messages[0])
        self.assertIn("结果：", sent_messages[0])
        self.assertIn("计算摘要：", sent_messages[0])
        self.assertNotIn("范围：参考范围", sent_messages[0])
        self.assertNotIn("正文预览：", sent_messages[0])

    def test_protein_template_requires_full_report_md_from_ai(self):
        definition = app_module.template_registry.get("protein_calculation")
        globals_dict = definition.render_callable.__globals__
        original_service = globals_dict["DoubaoSeed16Service"]
        original_feishu = globals_dict["FeishuBotClient"]
        sent_messages = []

        class _FakeService:
            def generate_structured_json(self, **kwargs):
                return {"intro": "只有开场，没有完整正文"}

        class _FakeFeishuBotClient:
            def send_text(self, text):
                sent_messages.append(text)

        globals_dict["DoubaoSeed16Service"] = _FakeService
        globals_dict["FeishuBotClient"] = _FakeFeishuBotClient
        try:
            with self.assertRaises(RuntimeError) as ctx:
                definition.render(
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
            globals_dict["DoubaoSeed16Service"] = original_service
            globals_dict["FeishuBotClient"] = original_feishu

        self.assertIn("report_md", str(ctx.exception))
        self.assertEqual(len(sent_messages), 1)
        self.assertIn("蛋白质模板执行失败", sent_messages[0])
        self.assertIn("用户昵称：测试用户", sent_messages[0])
        self.assertIn("关键信息：", sent_messages[0])
        self.assertIn("report_md", sent_messages[0])


if __name__ == "__main__":
    unittest.main()
