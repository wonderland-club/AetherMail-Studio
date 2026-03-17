"""
邮件地址验证工具
"""
import re

def validate_email(email: str) -> bool:
    """验证邮件地址格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
