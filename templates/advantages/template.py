from pathlib import Path

TEMPLATE_ID = "advantages"
DESCRIPTION = "优点清单"
DEFAULT_SUBJECT = "陈总万岁，来自俊俊的爱意存档"
REQUIRED_FIELDS = []

def render(data, renderer):
    """渲染优点清单模板"""
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")
    # 无占位符，但保持接口一致
    return renderer.render(md_text, data or {})
