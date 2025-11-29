"""
邮件发送系统配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# SMTP配置
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.qq.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# 邮件配置（不提供默认值，需在环境变量中显式设置）
DEFAULT_SENDER_NAME = os.getenv('DEFAULT_SENDER_NAME')
DEFAULT_SUBJECT_PREFIX = os.getenv('DEFAULT_SUBJECT_PREFIX')

# 验证必要的配置
if not SMTP_USER or not SMTP_PASSWORD:
    raise ValueError("请在.env文件中配置SMTP_USER和SMTP_PASSWORD")

print(f"✅ 邮件配置加载成功: {SMTP_USER}")