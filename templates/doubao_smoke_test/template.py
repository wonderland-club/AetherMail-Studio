from pathlib import Path

from src.ai import AIResponseError, DoubaoSeed16Service, normalize_markdown

TEMPLATE_ID = "doubao_smoke_test"
DESCRIPTION = "doubao-seed-1.6 链路验证模板（真实 AI 调用）"
DEFAULT_SUBJECT = "doubao-seed-1.6 链路验证邮件"
REQUIRED_FIELDS = ["TOPIC"]


def _build_prompt(name: str, topic: str) -> str:
    return f"""
你是一名温暖、真诚、能量感很强的中文邮件助手。请围绕给定主题，为收件人写两句简短的话。

要求：
1. 只输出两句话，不要多，不要少。
2. 第一句：给收件人一个祝福语。
3. 第二句：给收件人一个正反馈，语气积极、鼓舞、能量满满。
4. 使用自然中文，直接对收件人说话。
5. 不要标题，不要列表，不要署名，不要解释。
6. 两句话放在同一个 `report_md` 字段里，直接返回 JSON 字符串，不要添加代码块标记。

收件人称呼：{name}
主题：{topic}
"""


def render(data, renderer):
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")

    incoming = dict(data or {})
    name = (incoming.get("NAME") or "朋友").strip() or "朋友"
    topic = str(incoming.get("TOPIC") or "").strip()

    service = DoubaoSeed16Service()
    result = service.generate_structured_json(
        prompt=_build_prompt(name, topic),
        schema_name="doubao_smoke_test",
        schema_description="Two energetic Chinese sentences: one blessing and one positive affirmation.",
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
