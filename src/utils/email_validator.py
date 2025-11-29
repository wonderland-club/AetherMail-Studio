"""
邮件地址验证工具
"""
import re
from typing import Dict, Any, List

def validate_email(email: str) -> bool:
    """验证邮件地址格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_request_data(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, str]:
    """验证请求数据"""
    errors = {}
    
    # 检查必需字段
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = f"字段 {field} 是必需的"
    
    # 验证邮箱字段
    email_fields = ['mail_recipient', 'spaceone_mail_recipient']
    for field in email_fields:
        if field in data and data[field]:
            if not validate_email(data[field]):
                errors[field] = f"邮箱地址格式不正确: {data[field]}"
    
    return errors