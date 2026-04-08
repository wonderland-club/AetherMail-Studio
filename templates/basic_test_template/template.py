from datetime import datetime
from pathlib import Path

TEMPLATE_ID = "basic_test_template"
DESCRIPTION = "普通测试模板"
DEFAULT_SUBJECT = "普通测试邮件"
REQUIRED_FIELDS = ["MESSAGE"]


def render(data, renderer):
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")
    data = dict(data or {})

    data.setdefault("CURRENT_TIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return renderer.render(md_text, data)
