from pathlib import Path

from src.ai import AIResponseError, DoubaoService, normalize_markdown

TEMPLATE_ID = "doubao_smoke_test"
DESCRIPTION = "豆包链路验证模板（真实 AI 调用）"
DEFAULT_SUBJECT = "豆包链路验证邮件"
REQUIRED_FIELDS = ["TOPIC"]


def _build_prompt(name: str, topic: str) -> str:
    return f"""
你是一名专业、简洁的中文邮件助手。请围绕给定主题生成一封用于链路验证的 Markdown 邮件正文。

要求：
1. 使用自然中文。
2. 正文必须包含：
   - 1 个一级标题
   - 1 段简短摘要
   - 1 个 3 条的无序列表
3. 内容聚焦主题本身，不要输出解释你如何生成内容。
4. 直接返回 JSON 字符串，不要添加代码块标记。

收件人称呼：{name}
主题：{topic}
"""


def render(data, renderer):
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")

    incoming = dict(data or {})
    name = (incoming.get("NAME") or "朋友").strip() or "朋友"
    topic = str(incoming.get("TOPIC") or "").strip()

    service = DoubaoService()
    result = service.generate_structured_json(
        prompt=_build_prompt(name, topic),
        schema_name="doubao_smoke_test",
        schema_description="Minimal Markdown email body for Doubao integration smoke test.",
        schema={
            "type": "object",
            "properties": {
                "report_md": {"type": "string"},
            },
            "required": ["report_md"],
            "additionalProperties": False,
        },
        strict=True,
    )
    ai_report = normalize_markdown((result.get("report_md") or "").strip())
    if not ai_report:
        raise AIResponseError("AI 文案为空，无法渲染验证邮件")

    payload = {
        "NAME": name,
        "AI_REPORT": ai_report,
    }
    return renderer.render(md_text, payload)
