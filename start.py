#!/usr/bin/env python3
"""
快速启动脚本 - 俊俊的Markdown邮件发送系统

这个脚本会自动检查环境配置并启动邮件发送系统。
"""
import logging
import os
import sys
import subprocess

from src.config import load_env
from src.logging_setup import configure_logging

logger = logging.getLogger("start")

def check_python_version():
    """检查Python版本"""
    logger.info("check_python_version")
    if sys.version_info < (3, 7):
        logger.error("python_version_too_low")
        return False
    logger.info("python_version_ok | version=%s", sys.version.split()[0])
    return True

def check_dependencies():
    """检查依赖包"""
    logger.info("check_dependencies")
    
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
            logger.info("dependency_ok | package=%s", pkg_name)
        except ImportError:
            logger.warning("dependency_missing | package=%s", pkg_name)
            missing_packages.append(pkg_name)
    
    if missing_packages:
        logger.error("missing_dependencies | packages=%s", " ".join(missing_packages))
        return False
    
    return True

def check_env_config():
    """检查环境配置"""
    logger.info("check_env_config")
    
    if not os.path.exists('.env'):
        print("❌ .env文件不存在")
        print("💡 请复制 .env.example 为 .env，并配置 SMTP_PROFILES、DEFAULT_SMTP_NAME 和对应的 SMTP_PROFILE_*")
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
    logger.info("check_template_files")
    
    template_file = "templates/advantages/template.md"
    if not os.path.exists(template_file):
        logger.error("template_missing | path=%s", template_file)
        return False
    
    logger.info("template_ok | path=%s", template_file)
    return True

def run_tests():
    """运行基础测试"""
    logger.info("run_tests")
    
    try:
        # 运行SMTP连接测试
        result = subprocess.run([sys.executable, 'test_smtp.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info("test_smtp_ok")
        else:
            print("❌ SMTP连接测试失败")
            print(result.stdout or result.stderr)
            return False

        return True
        
    except subprocess.TimeoutExpired:
        logger.error("tests_timeout")
        return False
    except Exception as e:
        logger.exception("tests_exception | error=%s", e)
        return False

def start_server():
    """启动Flask服务器"""
    logger.info("server_starting | address=http://127.0.0.1:5000")
    
    try:
        env = os.environ.copy()
        env["APP_LOG_RESET_DONE"] = "1"
        subprocess.run([sys.executable, 'app.py'], env=env)
    except KeyboardInterrupt:
        logger.info("server_stopped")

def main():
    """主函数"""
    load_env()
    configure_logging(force=True)
    logger.info("startup_checks_begin")
    
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
            logger.error("startup_check_failed | check=%s", check_name)
            return False
    
    logger.info("startup_checks_ok")
    
    # 询问是否运行测试
    try:
        choice = input("是否运行基础测试？(推荐) [y/N]: ").lower().strip()
        if choice in ['y', 'yes']:
            if not run_tests():
                logger.warning("tests_failed_continue_prompt")
                choice = input("测试失败，是否继续启动服务器？ [y/N]: ").lower().strip()
                if choice not in ['y', 'yes']:
                    return False
    except KeyboardInterrupt:
        logger.info("startup_cancelled")
        return False
    
    # 启动服务器
    start_server()
    return True

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("startup_cancelled")
    except Exception as e:
        print(f"\n💥 启动过程中出现异常: {e}")
        sys.exit(1)
