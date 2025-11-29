#!/usr/bin/env python3
"""
新版邮件发送示例脚本：统一的 /api/send 接口
"""
import json
import requests

API_BASE_URL = "http://127.0.0.1:5000"


def check_api_status():
    """检查API服务器状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        ok = response.status_code == 200
        print("✅ API服务器运行正常" if ok else "❌ API服务器状态异常")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 无法连接到API服务器: {exc}")
        return False


def get_available_templates():
    """获取可用的模板列表"""
    try:
        response = requests.get(f"{API_BASE_URL}/templates")
        if response.status_code != 200:
            print("❌ 获取模板列表失败")
            return []
        data = response.json().get('templates', [])
        print(f"📝 可用模板数量: {len(data)}")
        for item in data:
            print(f"  - {item.get('id')} (需要字段: {item.get('required_fields')})")
        return [item.get('id') for item in data]
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 获取模板列表时发生错误: {exc}")
        return []


def send_email_with_template(template_id, to_email, data=None, cc=None):
    """使用统一接口发送邮件"""
    payload = {
        "template": template_id,
        "to": to_email,
        "cc": cc or [],
        "data": data or {},
    }
    try:
        response = requests.post(f"{API_BASE_URL}/api/send", json=payload)
        print(f"\n发送模板 {template_id} 到 {to_email}")
        print(f"状态码: {response.status_code}")
        try:
            resp_json = response.json()
        except Exception:
            resp_json = response.text
        print(f"响应: {json.dumps(resp_json, ensure_ascii=False, indent=2) if isinstance(resp_json, dict) else resp_json}")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 发送邮件时发生错误: {exc}")


def main():
    print("🚀 新版邮件发送系统示例")
    print("=" * 50)

    if not check_api_status():
        print("请先启动API服务器: python app.py")
        return

    print("\n2. 获取可用模板...")
    templates = get_available_templates()
    if not templates:
        print("没有可用的模板")
        return

    recipient = "junyan101@qq.com"  # 请替换为真实收件人
    print(f"\n3. 开始发送邮件到: {recipient}")

    # 发送优点清单（无占位符）
    send_email_with_template("advantages", recipient)

    # 发送通知模板（包含占位符）
    send_email_with_template(
        "notification",
        recipient,
        data={"MESSAGE": "上线提醒", "CURRENT_TIME": "2024-06-01 12:00"}
    )

    print("\n✅ 示例演示完成！")


if __name__ == "__main__":
    main()
