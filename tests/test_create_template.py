import tempfile
import unittest
from pathlib import Path

from create_template import create_template_scaffold
from src.core.renderer import Renderer
from src.core.template_registry import TemplateRegistry


class CreateTemplateTests(unittest.TestCase):
    def test_generated_template_matches_unified_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            target_dir = create_template_scaffold(
                repo_root=repo_root,
                template_id="demo_notice",
                subject="测试主题",
                description="测试通知模板",
            )

            self.assertTrue((target_dir / "template.py").exists())
            self.assertTrue((target_dir / "template.md").exists())
            self.assertTrue((target_dir / "attachments" / "README.md").exists())
            self.assertTrue((target_dir / "attachments" / "slot1").is_dir())
            self.assertTrue((target_dir / "attachments" / "slot2").is_dir())
            self.assertTrue((target_dir / "attachments" / "slot3").is_dir())

            template_py = (target_dir / "template.py").read_text(encoding="utf-8")
            template_md = (target_dir / "template.md").read_text(encoding="utf-8")
            self.assertIn("def _maybe_generate_ai_report(payload):", template_py)
            self.assertIn('payload.setdefault("AI_REPORT", "")', template_py)
            self.assertIn("{{&AI_REPORT}}", template_md)

            registry = TemplateRegistry(templates_root=repo_root / "templates")
            definition = registry.get("demo_notice")
            self.assertIsNotNone(definition)
            self.assertEqual(definition.default_subject, "测试主题")
            self.assertEqual(definition.attachment_slots, ["slot1", "slot2", "slot3"])

            rendered = definition.render({}, Renderer())
            self.assertIn("您好，", rendered)
            self.assertIn("请在此填写邮件正文。", rendered)
            self.assertNotIn("{{&AI_REPORT}}", rendered)

    def test_generated_template_can_enable_ai_hook_later(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            target_dir = create_template_scaffold(
                repo_root=repo_root,
                template_id="demo_notice",
                subject="测试主题",
            )

            template_py_path = target_dir / "template.py"
            original = template_py_path.read_text(encoding="utf-8")
            upgraded = original.replace('    return ""', '    return "# AI 内容\\n\\n- 第一条\\n- 第二条\\n- 第三条"', 1)
            template_py_path.write_text(upgraded, encoding="utf-8")

            registry = TemplateRegistry(templates_root=repo_root / "templates")
            definition = registry.get("demo_notice")
            rendered = definition.render({}, Renderer())
            self.assertIn("# AI 内容", rendered)
            self.assertIn("- 第一条", rendered)


if __name__ == "__main__":
    unittest.main()
