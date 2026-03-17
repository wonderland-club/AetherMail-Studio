"""
邮件发送系统配置文件
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DEFAULT_SECURE_MODE = 'ssl'


@dataclass(frozen=True)
class SMTPProfile:
    """单个SMTP主体配置"""

    smtp_name: str
    name: str
    host: str
    port: int
    secure: str
    user: str
    password: str
    sender_name: Optional[str] = None
    is_default: bool = False
    source: str = 'env'

    def to_dict(self, include_password: bool = False) -> Dict[str, object]:
        """导出配置字典，默认脱敏密码"""
        data = {
            'smtp_name': self.smtp_name,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'secure': self.secure,
            'user': self.user,
            'sender_name': self.sender_name,
            'is_default': self.is_default,
            'source': self.source,
            'password_configured': bool(self.password),
        }
        data['password'] = self.password if include_password else _mask_secret(self.password)
        return data


def _split_csv(raw_value: Optional[str]) -> List[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(',') if item.strip()]


def _normalize_secure_mode(raw_value: Optional[str]) -> str:
    if not raw_value:
        return DEFAULT_SECURE_MODE

    secure_mode = raw_value.strip().lower()
    secure_aliases = {
        'ssl': 'ssl',
        'smtps': 'ssl',
        'tls': 'tls',
        'starttls': 'tls',
    }
    if secure_mode not in secure_aliases:
        raise ValueError(f"不支持的 SMTP 安全模式: {raw_value}")
    return secure_aliases[secure_mode]


def _normalize_profile_key(smtp_name: str) -> str:
    return smtp_name.strip().upper().replace('-', '_')


def _mask_secret(secret: Optional[str]) -> str:
    if not secret:
        return ''
    if len(secret) <= 4:
        return '*' * len(secret)
    return f"{secret[:2]}{'*' * (len(secret) - 4)}{secret[-2:]}"


def _build_profile_from_group(smtp_name: str, is_default: bool) -> SMTPProfile:
    profile_key = _normalize_profile_key(smtp_name)
    env_prefix = f'SMTP_PROFILE_{profile_key}_'

    host = os.getenv(f'{env_prefix}HOST')
    port_raw = os.getenv(f'{env_prefix}PORT', '465')
    secure = _normalize_secure_mode(os.getenv(f'{env_prefix}SECURE', DEFAULT_SECURE_MODE))
    user = os.getenv(f'{env_prefix}USER')
    password = os.getenv(f'{env_prefix}PASSWORD')
    name = os.getenv(f'{env_prefix}NAME', smtp_name)
    sender_name = os.getenv(f'{env_prefix}SENDER_NAME')

    missing_fields = []
    if not host:
        missing_fields.append(f'{env_prefix}HOST')
    if not user:
        missing_fields.append(f'{env_prefix}USER')
    if not password:
        missing_fields.append(f'{env_prefix}PASSWORD')
    if missing_fields:
        raise ValueError(f"SMTP主体 {smtp_name} 缺少配置: {', '.join(missing_fields)}")

    try:
        port = int(port_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"SMTP主体 {smtp_name} 的端口无效: {port_raw}") from exc

    return SMTPProfile(
        smtp_name=smtp_name,
        name=name,
        host=host,
        port=port,
        secure=secure,
        user=user,
        password=password,
        sender_name=sender_name,
        is_default=is_default,
        source='env_profiles',
    )


def _load_smtp_profiles() -> List[SMTPProfile]:
    profile_names = _split_csv(os.getenv('SMTP_PROFILES'))
    if not profile_names:
        raise ValueError("请在.env文件中配置 SMTP_PROFILES，并为每个 smtp_name 提供完整的 SMTP_PROFILE_* 配置")

    default_smtp_name = os.getenv('DEFAULT_SMTP_NAME')
    if not default_smtp_name:
        raise ValueError("请在.env文件中配置 DEFAULT_SMTP_NAME，且其值必须出现在 SMTP_PROFILES 中")
    if default_smtp_name not in profile_names:
        raise ValueError(
            f"DEFAULT_SMTP_NAME={default_smtp_name} 不在 SMTP_PROFILES 列表中: {', '.join(profile_names)}"
        )

    return [
        _build_profile_from_group(smtp_name, is_default=(smtp_name == default_smtp_name))
        for smtp_name in profile_names
    ]


SMTP_PROFILES = _load_smtp_profiles()
SMTP_PROFILE_MAP = {profile.smtp_name.lower(): profile for profile in SMTP_PROFILES}
DEFAULT_SMTP_PROFILE = next(profile for profile in SMTP_PROFILES if profile.is_default)
DEFAULT_SMTP_NAME = DEFAULT_SMTP_PROFILE.smtp_name


def get_smtp_profile(identifier: Optional[str] = None) -> SMTPProfile:
    """按 smtp_name 获取SMTP主体；未指定时返回默认主体"""
    if not identifier:
        return DEFAULT_SMTP_PROFILE

    normalized_identifier = identifier.strip().lower()
    exact_match = SMTP_PROFILE_MAP.get(normalized_identifier)
    if exact_match:
        return exact_match

    raise KeyError(f"未找到SMTP主体: {identifier}")


def get_smtp_profiles_public(include_password: bool = False) -> List[Dict[str, object]]:
    """返回所有SMTP主体的公开配置"""
    return [profile.to_dict(include_password=include_password) for profile in SMTP_PROFILES]


print(
    f"✅ 邮件配置加载成功: 默认主体 {DEFAULT_SMTP_PROFILE.smtp_name} <{DEFAULT_SMTP_PROFILE.user}>，"
    f"共 {len(SMTP_PROFILES)} 个SMTP主体"
)
