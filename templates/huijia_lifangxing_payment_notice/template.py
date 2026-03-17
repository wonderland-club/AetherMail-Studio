from datetime import datetime
from pathlib import Path

TEMPLATE_ID = "huijia_lifangxing_payment_notice"
DESCRIPTION = "立方星项目缴费通知"
DEFAULT_SUBJECT = "汇佳立方星发射任务录取与缴费通知"
REQUIRED_FIELDS = ["NAME"]
ATTACHMENT_SLOTS = ["slot1", "slot2", "slot3"]


def render(data, renderer):
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")
    payload = dict(data or {})
    payload.setdefault("CURRENT_DATE", datetime.now().strftime("%Y-%m-%d"))
    return renderer.render(md_text, payload)
