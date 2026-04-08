import json
import unittest
from unittest.mock import patch

from src.feishu_bot import FeishuBotClient, FeishuBotConfigError, FeishuBotRequestError


class _FakeResponse:
    def __init__(self, status=200, body="{}"):
        self.status = status
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FeishuBotClientTests(unittest.TestCase):
    def test_send_text_builds_signed_payload(self):
        captured = {}

        def _fake_open(req, timeout):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _FakeResponse(body='{"StatusCode":0,"StatusMessage":"success"}')

        with patch("src.feishu_bot.client.time.time", return_value=1700000000):
            client = FeishuBotClient(
                webhook_url="https://example.com/hook",
                secret="secret-demo",
                timeout=5,
                opener=_fake_open,
            )
            result = client.send_text("hello feishu")

        self.assertTrue(result.ok)
        self.assertEqual(captured["url"], "https://example.com/hook")
        self.assertEqual(captured["timeout"], 5)
        self.assertEqual(captured["body"]["msg_type"], "text")
        self.assertEqual(captured["body"]["content"]["text"], "hello feishu")
        self.assertEqual(captured["body"]["timestamp"], "1700000000")
        self.assertEqual(
            captured["body"]["sign"],
            FeishuBotClient.build_sign("1700000000", "secret-demo"),
        )

    def test_send_text_requires_webhook(self):
        client = FeishuBotClient(webhook_url="", secret="")
        with self.assertRaises(FeishuBotConfigError):
            client.send_text("hello")

    def test_send_text_raises_on_feishu_error_response(self):
        def _fake_open(req, timeout):
            return _FakeResponse(body='{"code":19001,"msg":"invalid"}')

        client = FeishuBotClient(
            webhook_url="https://example.com/hook",
            secret="secret-demo",
            opener=_fake_open,
        )
        with self.assertRaises(FeishuBotRequestError):
            client.send_text("hello")


if __name__ == "__main__":
    unittest.main()
