"""邮件发送功能的标准库测试。

使用 mock 模拟 SMTP 交互，不发送真实邮件。
"""

from __future__ import annotations

import os
import smtplib
import unittest
from unittest.mock import MagicMock, patch

from agent.email_sender import send_plain_email
from agent.tool_result import ToolResult


class SendPlainEmailTests(unittest.TestCase):
    """覆盖正常发送和各类失败场景，全部使用 mock。"""

    def setUp(self) -> None:
        """设置测试环境变量（有效凭据以通过配置加载）。"""
        os.environ["QQ_EMAIL_ADDRESS"] = "sender@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "test_auth_code_16chars"
        os.environ["QQ_EMAIL_WHITELIST"] = ""  # 空白名单 = 允许所有，向后兼容

    def tearDown(self) -> None:
        """清理环境变量。"""
        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE", "QQ_EMAIL_WHITELIST"):
            os.environ.pop(key, None)

    # ── 成功场景 ──────────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_sends_email_successfully(self, mock_smtp_class: MagicMock) -> None:
        """模拟 SMTP 发送成功时应返回 success=True。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="receiver@qq.com")

        self.assertTrue(result.success)
        self.assertEqual(result.result.get("to_address"), "receiver@qq.com")
        self.assertEqual(result.error, "")
        mock_server.login.assert_called_once_with("sender@qq.com", "test_auth_code_16chars")
        mock_server.sendmail.assert_called_once()

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_uses_default_recipient(self, mock_smtp_class: MagicMock) -> None:
        """不指定收件人时使用默认地址。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_plain_email()

        self.assertTrue(result.success)
        self.assertEqual(result.result.get("to_address"), "1962383827@qq.com")

    # ── 失败场景：参数 ────────────────────────────────────────

    def test_rejects_empty_recipient(self) -> None:
        """空白收件人应返回错误。"""
        result = send_plain_email(to_address="  ")

        self.assertFalse(result.success)
        self.assertIn("不能为空", result.error)

    def test_rejects_missing_config(self) -> None:
        """缺少环境变量时应返回错误而不崩溃。"""
        # 清除环境变量后，load_dotenv 会从真实 .env 重载。
        # 因此改为直接模拟 load_qq_email_config 抛出异常。
        with patch("agent.email_sender.load_qq_email_config") as mock_load:
            mock_load.side_effect = ValueError("缺少必需的环境变量: QQ_EMAIL_ADDRESS")
            result = send_plain_email(to_address="receiver@qq.com")

        self.assertFalse(result.success)
        self.assertIn("缺少", result.error)

    # ── 失败场景：SMTP ────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_handles_auth_failure(self, mock_smtp_class: MagicMock) -> None:
        """SMTP 认证失败时应返回错误而不崩溃。"""
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"auth failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="receiver@qq.com")

        self.assertFalse(result.success)
        self.assertIn("认证失败", result.error)

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_handles_smtp_error(self, mock_smtp_class: MagicMock) -> None:
        """SMTP 通用错误时应返回错误而不崩溃。"""
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPException("send failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="receiver@qq.com")

        self.assertFalse(result.success)
        self.assertIn("SMTP 发送失败", result.error)

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_handles_network_error(self, mock_smtp_class: MagicMock) -> None:
        """网络连接失败时应返回错误而不崩溃。"""
        mock_smtp_class.side_effect = OSError("Connection refused")

        result = send_plain_email(to_address="receiver@qq.com")

        self.assertFalse(result.success)
        self.assertIn("网络连接失败", result.error)

    # ── 返回类型 ──────────────────────────────────────────────

    def test_returns_tool_result_instance(self) -> None:
        """返回值始终是 ToolResult 实例。"""
        result = send_plain_email(to_address="  ")
        self.assertIsInstance(result, ToolResult)

    # ── 安全：返回结果和日志不包含授权码 ──────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_result_does_not_contain_auth_code(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """验证返回的 ToolResult 中不包含授权码。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="receiver@qq.com")

        # params 中不包含授权码。
        self.assertNotIn("auth_code", result.params)
        self.assertNotIn("QQ_EMAIL_AUTH_CODE", str(result.params))
        self.assertNotIn("password", str(result.params))
        # result 字典中不包含授权码。
        self.assertNotIn("auth_code", result.result)
        # error 中不包含授权码。
        self.assertNotIn("test_auth_code_16chars", result.error)

    # ── 统一字段完整性 ───────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_tool_result_has_required_fields(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """ToolResult 应包含所有统一字段。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="receiver@qq.com")

        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, "send_email")
        self.assertIn("to_address", result.params)
        self.assertIn("subject", result.params)
        # 敏感信息不出现在 params 中。
        self.assertNotIn("auth_code", result.params)
        self.assertNotIn("body", result.params)  # 正文内容不记录在 params 中
        self.assertIn("body_length", result.params)  # 只记录长度
        self.assertIsInstance(result.timestamp, str)
        self.assertTrue(len(result.timestamp) > 0)
        self.assertIsInstance(result.audit_id, str)
        self.assertTrue(len(result.audit_id) > 0)


if __name__ == "__main__":
    unittest.main()
