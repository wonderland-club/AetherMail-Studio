#!/usr/bin/env python3
"""
创建新的空白邮件模板脚手架。
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

TEMPLATE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ATTACHMENT_SLOTS = ("slot1", "slot2", "slot3")


def _py_string_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def validate_template_id(template_id: str) -> None:
    if not TEMPLATE_ID_PATTERN.fullmatch(template_id):
        raise ValueError("template_id 必须是 ASCII snake_case，只能包含小写字母、数字、下划线，且需以字母开头")


def build_template_py(template_id: str, subject: str, description: str) -> str:
    return f"""from pathlib import Path

TEMPLATE_ID = {_py_string_literal(template_id)}
DESCRIPTION = {_py_string_literal(description)}
DEFAULT_SUBJECT = {_py_string_literal(subject)}
REQUIRED_FIELDS = []
ATTACHMENT_SLOTS = ["slot1", "slot2", "slot3"]


def _maybe_generate_ai_report(payload):
    \"\"\"Optional AI hook.

    默认不调用 AI，直接返回空字符串。
    如需启用，可在这里按需接入 src.ai 中的 DoubaoService / normalize_markdown，
    并返回要注入到 {{&AI_REPORT}} 的 Markdown 文本。
    \"\"\"
    return ""


def render(data, renderer):
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")
    payload = dict(data or {{}})

    ai_report = _maybe_generate_ai_report(payload)
    if ai_report:
        payload["AI_REPORT"] = ai_report
    else:
        payload.setdefault("AI_REPORT", "")

    return renderer.render(md_text, payload)
"""


def build_template_md() -> str:
    return (
        "<!-- 在此填写邮件正文，变量格式：&#123;&#123;&VAR&#125;&#125; -->\n\n"
        "您好，\n\n"
        "请在此填写邮件正文。\n\n"
        "{{&AI_REPORT}}\n"
    )


def build_attachments_readme(description: str) -> str:
    return f"""# {description} 附件槽位

此模板包含 3 个附件槽位：

- `slot1/`
- `slot2/`
- `slot3/`

使用规则：

1. 每个槽位目录里最多放 1 个真实附件文件。
2. 系统发送邮件时会自动读取这 3 个目录中的附件并附加到邮件。
3. 目录中的隐藏文件和 `README.md` 会被忽略。
4. 如果某个槽位没有文件，就会跳过该附件。
"""


def create_template_scaffold(
    repo_root: Path,
    template_id: str,
    subject: str,
    description: Optional[str] = None,
) -> Path:
    validate_template_id(template_id)

    templates_root = repo_root / "templates"
    target_dir = templates_root / template_id
    if target_dir.exists():
        raise FileExistsError(f"模板目录已存在: {target_dir}")

    resolved_description = description or subject
    attachments_root = target_dir / "attachments"

    target_dir.mkdir(parents=True, exist_ok=False)
    attachments_root.mkdir(parents=True, exist_ok=False)
    for slot in ATTACHMENT_SLOTS:
        (attachments_root / slot).mkdir()

    (target_dir / "template.py").write_text(
        build_template_py(template_id, subject, resolved_description),
        encoding="utf-8",
    )
    (target_dir / "template.md").write_text(build_template_md(), encoding="utf-8")
    (attachments_root / "README.md").write_text(
        build_attachments_readme(resolved_description),
        encoding="utf-8",
    )

    return target_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建新的空白邮件模板脚手架")
    parser.add_argument("--template-id", required=True, help="模板ID，使用 ASCII snake_case")
    parser.add_argument("--subject", required=True, help="默认邮件主题")
    parser.add_argument("--description", help="模板描述，默认等于 subject")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent

    try:
        target_dir = create_template_scaffold(
            repo_root=repo_root,
            template_id=args.template_id,
            subject=args.subject,
            description=args.description,
        )
    except (ValueError, FileExistsError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    print(f"✅ 模板已创建: {args.template_id}")
    print(f"📁 目录: {target_dir}")
    print(f"✉️  主题: {args.subject}")
    print("📎 附件槽位: slot1, slot2, slot3")
    print("📘 模板规范: templates/新增模板说明.md")
    print("🔄 如服务正在运行，请重启后再使用新模板")
    return 0


if __name__ == "__main__":
    sys.exit(main())
