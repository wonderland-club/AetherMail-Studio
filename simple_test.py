"""
简单的邮件发送测试 - 不使用复杂的Markdown转换
"""
import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.email_sender import EmailSender

def test_simple_email():
    """测试发送简单的HTML邮件"""
    print("📧 测试发送简单HTML邮件...")
    
    sender = EmailSender()
    
    # 简单的HTML内容
    html_content = """
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            h1 { color: #e74c3c; }
            p { margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>💕 测试邮件</h1>
        <p>这是一封测试邮件，用于验证邮件发送系统是否正常工作。</p>
        <p>如果您收到这封邮件，说明系统配置正确！</p>
        <p>来自：俊俊的Markdown邮件发送系统</p>
    </body>
    </html>
    """
    
    plain_text = """
    💕 测试邮件
    
    这是一封测试邮件，用于验证邮件发送系统是否正常工作。
    如果您收到这封邮件，说明系统配置正确！
    
    来自：俊俊的Markdown邮件发送系统
    """
    
    success, message = sender._send_email(
        html_content=html_content,
        plain_text=plain_text,
        recipient="junyan101@qq.com",
        subject="[💕爱意存档] 系统测试邮件"
    )
    
    if success:
        print(f"✅ 邮件发送成功: {message}")
        return True
    else:
        print(f"❌ 邮件发送失败: {message}")
        return False

if __name__ == '__main__':
    print("🧪 简单邮件发送测试")
    print("=" * 30)
    
    if test_simple_email():
        print("\n🎉 邮件发送功能正常！")
    else:
        print("\n💥 邮件发送失败。")
