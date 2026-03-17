"""
模板注册表 - 扫描 templates/<id>/template.py 并加载定义
"""
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class TemplateLoadError(Exception):
    """模板加载异常"""


@dataclass
class TemplateAttachment:
    """模板附件定义"""

    slot: str
    path: Path


@dataclass
class TemplateDefinition:
    template_id: str
    base_path: Path
    default_subject: str
    required_fields: List[str]
    render_callable: Callable[[Dict[str, Any], Any], str]
    description: str = ""
    attachment_slots: List[str] = field(default_factory=list)

    def render(self, data: Dict[str, Any], renderer) -> str:
        return self.render_callable(data, renderer)

    def attachments_for(self) -> List[TemplateAttachment]:
        """按模板约定加载附件槽位中的真实文件"""
        attachments_root = self.base_path / 'attachments'
        if not attachments_root.exists() or not self.attachment_slots:
            return []

        attachment_paths: List[TemplateAttachment] = []
        for slot in self.attachment_slots:
            slot_dir = attachments_root / slot
            if not slot_dir.exists():
                continue

            candidates = [
                path for path in sorted(slot_dir.iterdir())
                if path.is_file() and not path.name.startswith('.') and path.name != 'README.md'
            ]
            if len(candidates) > 1:
                raise ValueError(f"附件槽位 {slot} 中只能放 1 个文件，当前有 {len(candidates)} 个")
            if candidates:
                attachment_paths.append(TemplateAttachment(slot=slot, path=candidates[0]))

        return attachment_paths


class TemplateRegistry:
    """按目录加载模板定义"""

    def __init__(self, templates_root: Optional[Path] = None) -> None:
        # repo_root = .../src/.. = 项目根目录
        repo_root = Path(__file__).resolve().parents[2]
        self.templates_root = Path(templates_root or repo_root / 'templates')
        self.templates: Dict[str, TemplateDefinition] = {}
        self.reload()

    def _load_template(self, template_dir: Path) -> Optional[TemplateDefinition]:
        template_py = template_dir / 'template.py'
        if not template_py.exists():
            return None

        spec = importlib.util.spec_from_file_location(
            f"templates.{template_dir.name}.template", template_py
        )
        if spec is None or spec.loader is None:
            raise TemplateLoadError(f"无法为 {template_dir.name} 创建加载器")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        render_callable = getattr(module, 'render', None)
        if not callable(render_callable):
            raise TemplateLoadError(f"模板 {template_dir.name} 缺少可调用的 render(data, renderer)")

        template_id = getattr(module, 'TEMPLATE_ID', None)
        if not isinstance(template_id, str) or not template_id.strip():
            raise TemplateLoadError(f"模板 {template_dir.name} 必须显式提供非空字符串 TEMPLATE_ID")

        default_subject = getattr(module, 'DEFAULT_SUBJECT', None)
        if not isinstance(default_subject, str) or not default_subject.strip():
            raise TemplateLoadError(f"模板 {template_dir.name} 必须显式提供非空字符串 DEFAULT_SUBJECT")

        required_fields = getattr(module, 'REQUIRED_FIELDS', []) or []
        description = getattr(module, 'DESCRIPTION', '') or ''
        attachment_slots = getattr(module, 'ATTACHMENT_SLOTS', []) or []

        return TemplateDefinition(
            template_id=template_id,
            base_path=template_dir,
            default_subject=default_subject,
            required_fields=list(required_fields),
            render_callable=render_callable,
            description=description,
            attachment_slots=list(attachment_slots),
        )

    def reload(self) -> None:
        self.templates.clear()
        if not self.templates_root.exists():
            print(f"⚠️ 模板目录不存在: {self.templates_root}")
            return

        for child in sorted(self.templates_root.iterdir()):
            if not child.is_dir():
                continue
            try:
                definition = self._load_template(child)
                if definition:
                    self.templates[definition.template_id] = definition
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ 模板加载失败 {child.name}: {exc}")

    def get(self, template_id: str) -> Optional[TemplateDefinition]:
        return self.templates.get(template_id)

    def list_templates(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': definition.template_id,
                'description': definition.description,
                'default_subject': definition.default_subject,
                'required_fields': definition.required_fields,
                'attachment_slots': definition.attachment_slots,
            }
            for definition in self.templates.values()
        ]
