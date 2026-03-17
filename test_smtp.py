"""
简单的SMTP连接测试
"""
import argparse
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import get_smtp_profile, get_smtp_profiles_public


def create_smtp_client(profile, context):
    """按配置创建SMTP客户端"""
    if profile.secure == 'ssl':
        return smtplib.SMTP_SSL(profile.host, profile.port, context=context)

    server = smtplib.SMTP(profile.host, profile.port)
    server.ehlo()
    server.starttls(context=context)
    server.ehlo()
    return server


def list_smtp_configs():
    """列出当前所有SMTP主体"""
    print("📋 当前SMTP主体列表")
    print("=" * 60)
    for item in get_smtp_profiles_public():
        default_marker = " (默认)" if item['is_default'] else ""
        print(f"- smtp_name: {item['smtp_name']}{default_marker}")
        print(f"  name     : {item['name']}")
        print(f"  host     : {item['host']}:{item['port']} [{item['secure']}]")
        print(f"  user     : {item['user']}")
        print(f"  sender   : {item['sender_name'] or '-'}")
        print(f"  password : {item['password']}")


def test_smtp_connection(smtp_name=None):
    """测试SMTP连接"""
    try:
        profile = get_smtp_profile(smtp_name)
    except (KeyError, ValueError) as exc:
        message = exc.args[0] if exc.args else str(exc)
        print(f"❌ {message}")
        return False

    print("🔗 测试SMTP连接...")
    print(f"主体: {profile.smtp_name} / {profile.name}")
    print(f"服务器: {profile.host}:{profile.port} [{profile.secure}]")
    print(f"用户: {profile.user}")

    try:
        # 创建SSL上下文
        context = ssl.create_default_context()

        # 连接到SMTP服务器
        print("📡 正在连接到SMTP服务器...")
        server = create_smtp_client(profile, context)

        # 登录
        print("🔐 正在进行身份验证...")
        server.login(profile.user, profile.password)

        print("✅ SMTP连接和认证成功！")

        # 发送简单测试邮件
        print("📧 发送测试邮件...")

        msg = MIMEMultipart()
        msg['From'] = profile.user
        msg['To'] = profile.user  # 发送给自己
        msg['Subject'] = "SMTP测试邮件"

        body = "这是一封SMTP连接测试邮件。如果您收到这封邮件，说明配置正确！"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server.sendmail(profile.user, [profile.user], msg.as_string())
        server.quit()

        print("✅ 测试邮件发送成功！")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 认证失败: {e}")
        print("请检查:")
        print("1. 邮箱地址是否正确")
        print("2. SMTP授权码是否正确（不是邮箱登录密码）")
        print("3. 是否已开启SMTP服务")
        return False

    except smtplib.SMTPConnectError as e:
        print(f"❌ 连接失败: {e}")
        print("请检查:")
        print("1. 网络连接是否正常")
        print("2. 防火墙是否阻止了连接")
        print("3. SMTP服务器地址和端口是否正确")
        return False

    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SMTP连接测试工具')
    parser.add_argument('--smtp-name', help='指定要测试的 smtp_name')
    parser.add_argument('--list', action='store_true', help='仅列出当前SMTP主体')
    args = parser.parse_args()

    print("🧪 SMTP连接测试工具")
    print("=" * 40)

    if args.list:
        list_smtp_configs()
        sys.exit(0)

    if test_smtp_connection(args.smtp_name):
        print("\n🎉 SMTP配置正确，可以发送邮件！")
        sys.exit(0)
    else:
        print("\n💥 SMTP配置有问题，请检查配置。")
        sys.exit(1)
