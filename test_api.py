#!/usr/bin/env python3
"""
测试统一的发送接口
"""
import json
import requests

API_BASE_URL = "http://127.0.0.1:5000"


def test_api_endpoint(endpoint: str, method: str = "GET", data=None):
    """测试API端点"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        else:
            response = requests.post(url, json=data)

        print(f"\n{'='*50}")
        print(f"测试: {method} {endpoint}")
        print(f"状态码: {response.status_code}")
        try:
            resp_json = response.json()
        except Exception:
            resp_json = response.text
        print(f"响应: {json.dumps(resp_json, ensure_ascii=False, indent=2) if isinstance(resp_json, dict) else resp_json}")
        return response.status_code
    except Exception as exc:  # noqa: BLE001
        print(f"请求失败: {exc}")
        return None


def main():
    print("🧪 开始测试统一API接口...")

    test_api_endpoint("/")
    test_api_endpoint("/health")
    test_api_endpoint("/templates")

    # 发送通知模板（包含占位符数据）
    email_data = {
        "template": "notification",
        "to": "someone@example.com",
        "cc": [],
        "data": {"MESSAGE": "上线提醒", "CURRENT_TIME": "2024-06-01 12:00"}
    }
    test_api_endpoint("/api/send", "POST", email_data)

    # 错误示例：缺少必需字段
    bad_data = {"template": "notification", "to": "invalid-email", "data": {}}
    test_api_endpoint("/api/send", "POST", bad_data)

    print("\n✅ API测试完成！")


if __name__ == "__main__":
    main()
