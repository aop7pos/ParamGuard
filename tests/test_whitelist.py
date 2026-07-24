"""收件人白名单功能的测试。

验证：
- 白名单邮箱可以正常发送。
- 非白名单邮箱在发送前被拦截。
- 即使确认发送，非白名单也不能发出。
- 被拒时记录目标邮箱和原因。
- 白名单为空时允许所有（向后兼容）。
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from agent.email_sender import send_plain_email


class WhitelistTests(unittest.TestCase):
    """覆盖白名单的通过、拦截和边界场景。"""

    def setUp(self) -> None:
        os.environ["QQ_EMAIL_ADDRESS"] = "sender@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "test_auth_code_16chars"

    def tearDown(self) -> None:
        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE", "QQ_EMAIL_WHITELIST"):
            os.environ.pop(key, None)

    # ── 白名单通过 ────────────────────────────────────────────

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_whitelisted_address_allowed(
        self, mock_smtp: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """白名单中的邮箱应能正常发送。"""
        mock_whitelist.return_value = ["trusted@qq.com"]
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="trusted@qq.com")

        self.assertTrue(result.success)
        mock_server.sendmail.assert_called_once()

    # ── 白名单拦截 ────────────────────────────────────────────

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_non_whitelisted_address_blocked(
        self, mock_smtp: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """非白名单邮箱应在发送前被拦截，不调用 SMTP。"""
        mock_whitelist.return_value = ["trusted@qq.com"]

        result = send_plain_email(to_address="evil@hacker.com")

        self.assertFalse(result.success)
        self.assertIn("不在白名单中", result.error)
        self.assertIn("evil@hacker.com", result.error)
        # SMTP 绝不应被调用。
        mock_smtp.assert_not_called()

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_blocked_before_smtp_connection(
        self, mock_smtp: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """拦截发生在 SMTP 连接之前，不消耗网络资源。"""
        mock_whitelist.return_value = ["allowed@qq.com"]

        send_plain_email(to_address="blocked@qq.com")

        # SMTP_SSL 从未被实例化。
        mock_smtp.assert_not_called()

    # ── 白名单为空（向后兼容） ───────────────────────────────

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_empty_whitelist_allows_all(
        self, mock_smtp: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """白名单为空时允���所有地址（向后兼容）。"""
        mock_whitelist.return_value = []
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="anyone@example.com")

        self.assertTrue(result.success)

    # ── 拒绝日志 ──────────────────────────────────────────────

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.write_audit_log")
    def test_rejection_is_logged(
        self, mock_log: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """被拒绝时应记录目标邮箱和拒绝原因到统一审计日志。"""
        mock_whitelist.return_value = ["safe@qq.com"]

        send_plain_email(to_address="bad@qq.com", subject="拦截测试")

        mock_log.assert_called_once()
        tr = mock_log.call_args[0][0]  # ToolResult passed as first arg
        self.assertEqual(tr.tool_name, "send_email")
        self.assertFalse(tr.success)
        self.assertEqual(tr.error_type, "whitelist")
        self.assertIn("不在白名单中", tr.error)
        self.assertIn("bad@qq.com", tr.error)

    # ── 日志不含敏感信息 ─────────────────────────────────────

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.write_audit_log")
    def test_rejection_log_no_sensitive_data(
        self, mock_log: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """拒绝日志不应包含授权码或密码。"""
        mock_whitelist.return_value = ["safe@qq.com"]

        send_plain_email(to_address="bad@qq.com")

        tr = mock_log.call_args[0][0]
        self.assertNotIn("auth_code", tr.params)
        self.assertNotIn("password", str(tr.params))
        self.assertNotIn("QQ_EMAIL_AUTH_CODE", str(tr.params))

    # ── 多地址白名单 ─────────────────────────────────────────

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_multiple_whitelist_addresses(
        self, mock_smtp: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """白名单中有多个地址时，任一匹配即可发送。"""
        mock_whitelist.return_value = ["a@qq.com", "b@qq.com", "c@qq.com"]
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="b@qq.com")

        self.assertTrue(result.success)

    @patch("agent.email_sender.load_whitelist")
    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_not_in_multiple_whitelist_still_blocked(
        self, mock_smtp: MagicMock, mock_whitelist: MagicMock
    ) -> None:
        """多地址白名单中无匹配时仍然拦截。"""
        mock_whitelist.return_value = ["a@qq.com", "b@qq.com"]

        result = send_plain_email(to_address="z@qq.com")

        self.assertFalse(result.success)
        self.assertIn("不在白名单中", result.error)

    # ── load_whitelist 函数本身 ───────────────────────────────

    def test_load_whitelist_parses_comma_separated(self) -> None:
        """load_whitelist 应正确解析逗号分隔的白名单。"""
        os.environ["QQ_EMAIL_WHITELIST"] = " a@qq.com , b@qq.com , c@qq.com "

        from agent.config import load_whitelist
        with patch("agent.config._load_dotenv"):
            whitelist = load_whitelist()

        self.assertEqual(whitelist, ["a@qq.com", "b@qq.com", "c@qq.com"])

    def test_load_whitelist_empty_when_not_set(self) -> None:
        """未设置白名单时返回空列表。"""
        from agent.config import load_whitelist
        with patch("agent.config._load_dotenv"):
            whitelist = load_whitelist()

        self.assertEqual(whitelist, [])


if __name__ == "__main__":
    unittest.main()
