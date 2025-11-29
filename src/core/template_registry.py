"""
模板注册表 - 扫描 templates/<id>/template.py 并加载定义
"""
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class TemplateLoadError(Exception):
    """模板加载异常"""


@dataclass
class TemplateDefinition:
    template_id: str
    base_path: Path
    default_subject: str
    required_fields: List[str]
    render_callable: Callable[[Dict[str, Any], Any], str]
    get_subject_callable: Optional[Callable[[Dict[str, Any]], str]] = None
    description: str = ""

    def render(self, data: Dict[str, Any], renderer) -> str:
        return self.render_callable(data, renderer)

    def subject_for(self, data: Dict[str, Any]) -> str:
        if callable(self.get_subject_callable):
            subject = self.get_subject_callable(data)
            if subject:
                return subject
        return self.default_subject


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

        template_id = getattr(module, 'TEMPLATE_ID', template_dir.name)
        default_subject = getattr(module, 'DEFAULT_SUBJECT', f"来自邮件系统的{template_id}")
        required_fields = getattr(module, 'REQUIRED_FIELDS', []) or []
        get_subject_callable = getattr(module, 'get_subject', None)
        description = getattr(module, 'DESCRIPTION', '') or ''

        return TemplateDefinition(
            template_id=template_id,
            base_path=template_dir,
            default_subject=default_subject,
            required_fields=list(required_fields),
            render_callable=render_callable,
            get_subject_callable=get_subject_callable,
            description=description,
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
            }
            for definition in self.templates.values()
        ]
