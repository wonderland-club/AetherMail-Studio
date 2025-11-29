"""
简单的SMTP连接测试
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

def test_smtp_connection():
    """测试SMTP连接"""
    print("🔗 测试SMTP连接...")
    print(f"服务器: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"用户: {SMTP_USER}")
    
    try:
        # 创建SSL上下文
        context = ssl.create_default_context()
        
        # 连接到SMTP服务器
        print("📡 正在连接到SMTP服务器...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context)
        
        # 登录
        print("🔐 正在进行身份验证...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        print("✅ SMTP连接和认证成功！")
        
        # 发送简单测试邮件
        print("📧 发送测试邮件...")
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = SMTP_USER  # 发送给自己
        msg['Subject'] = "SMTP测试邮件"
        
        body = "这是一封SMTP连接测试邮件。如果您收到这封邮件，说明配置正确！"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server.sendmail(SMTP_USER, [SMTP_USER], msg.as_string())
        server.quit()
        
        print("✅ 测试邮件发送成功！")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 认证失败: {e}")
        print("请检查:")
        print("1. QQ邮箱地址是否正确")
        print("2. SMTP授权码是否正确（不是QQ密码）")
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
    print("🧪 SMTP连接测试工具")
    print("=" * 40)
    
    if test_smtp_connection():
        print("\n🎉 SMTP配置正确，可以发送邮件！")
    else:
        print("\n💥 SMTP配置有问题，请检查配置。")