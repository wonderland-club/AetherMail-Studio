#!/usr/bin/env python3
"""
快速启动脚本 - 俊俊的Markdown邮件发送系统

这个脚本会自动检查环境配置并启动邮件发送系统。
"""
import os
import sys
import subprocess
import time

def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        return False
    print(f"✅ Python版本: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包...")
    
    # 使用映射来处理包名与导入名不一致的情况（例如 python-dotenv -> dotenv）
    required_packages = {
        'flask': 'flask',
        'pypandoc': 'pypandoc',
        'premailer': 'premailer',
        'python-dotenv': 'dotenv',
        'email-validator': 'email_validator',
    }

    missing_packages = []

    for pkg_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {pkg_name}")
        except ImportError:
            print(f"❌ {pkg_name} (缺失)")
            missing_packages.append(pkg_name)
    
    if missing_packages:
        print(f"\n💡 安装缺失的依赖包:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_env_config():
    """检查环境配置"""
    print("\n⚙️ 检查环境配置...")
    
    if not os.path.exists('.env'):
        print("❌ .env文件不存在")
        print("💡 请在项目根目录创建 .env，并配置 SMTP_PROFILES、DEFAULT_SMTP_NAME 和对应的 SMTP_PROFILE_*")
        return False
    
    # 检查必要的环境变量
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from src.config import get_smtp_profiles_public
        smtp_profiles = get_smtp_profiles_public()
    except Exception as exc:
        print(f"❌ SMTP配置无效: {exc}")
        print("💡 请检查 .env 中的 SMTP_PROFILES、DEFAULT_SMTP_NAME 以及对应的 SMTP_PROFILE_* 配置")
        return False

    print(f"✅ 环境配置完整，已加载 {len(smtp_profiles)} 个SMTP主体")
    return True

def check_template_files():
    """检查模板文件"""
    print("\n📄 检查模板文件...")
    
    template_file = "templates/advantages/template.md"
    if not os.path.exists(template_file):
        print(f"❌ 模板文件不存在: {template_file}")
        return False
    
    print(f"✅ 模板文件存在: {template_file}")
    return True

def run_tests():
    """运行基础测试"""
    print("\n🧪 运行基础测试...")
    
    try:
        # 运行SMTP连接测试
        result = subprocess.run([sys.executable, 'test_smtp.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ SMTP连接测试通过")
        else:
            print("❌ SMTP连接测试失败")
            print(result.stdout or result.stderr)
            return False

        return True
        
    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def start_server():
    """启动Flask服务器"""
    print("\n🚀 启动邮件发送系统...")
    print("=" * 50)
    print("💕 俊俊的Markdown邮件发送系统")
    print("🌐 服务器地址: http://127.0.0.1:5000")
    print("📧 API文档: http://127.0.0.1:5000")
    print("⏹️  按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")

def main():
    """主函数"""
    print("💕 俊俊的Markdown邮件发送系统 - 启动检查")
    print("=" * 60)
    
    # 检查列表
    checks = [
        ("Python版本", check_python_version),
        ("依赖包", check_dependencies),
        ("环境配置", check_env_config),
        ("模板文件", check_template_files),
    ]
    
    # 执行检查
    for check_name, check_func in checks:
        if not check_func():
            print(f"\n💥 {check_name}检查失败，请修复后重试")
            return False
    
    print("\n✅ 所有检查通过！")
    
    # 询问是否运行测试
    print("\n🤔 是否运行基础测试？(推荐) [y/N]: ", end="")
    try:
        choice = input().lower().strip()
        if choice in ['y', 'yes']:
            if not run_tests():
                print("\n💥 测试失败，但您仍可以尝试启动服务器")
                print("🤔 是否继续启动服务器？ [y/N]: ", end="")
                choice = input().lower().strip()
                if choice not in ['y', 'yes']:
                    return False
    except KeyboardInterrupt:
        print("\n👋 用户取消")
        return False
    
    # 启动服务器
    start_server()
    return True

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 启动已取消")
    except Exception as e:
        print(f"\n💥 启动过程中出现异常: {e}")
        sys.exit(1)
