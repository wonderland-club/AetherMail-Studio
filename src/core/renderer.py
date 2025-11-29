"""
模板渲染器 - 负责处理 {{&VAR}} 占位符
"""
import json
import re
from typing import Any, Dict, Set


class Renderer:
    """将 {{&VAR}} 占位符替换为请求体提供的数据"""

    def __init__(self) -> None:
        # 变量名允许字母、数字和下划线
        self.placeholder_pattern = re.compile(r"\{\{\&([A-Za-z0-9_]+)\}\}")

    def extract_placeholders(self, template_text: str) -> Set[str]:
        """获取模板中出现的占位符名称"""
        return set(self.placeholder_pattern.findall(template_text or ""))

    def render(self, template_text: str, data: Dict[str, Any]) -> str:
        """用 data 替换 {{&VAR}} 占位符"""
        data = data or {}
        placeholders = self.extract_placeholders(template_text)
        missing = [key for key in sorted(placeholders) if key not in data or data[key] is None]
        if missing:
            raise ValueError(f"缺少模板变量: {', '.join(missing)}")

        def replacer(match: re.Match) -> str:
            key = match.group(1)
            value = data.get(key)
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

        return self.placeholder_pattern.sub(replacer, template_text)
