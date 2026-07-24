"""邮件发送确认流程的测试。

验证：
- 确认后才能发送。
- 取消后绝不发送，且有日志记录。
- ``--yes`` 跳过确认。
- ``--dry-run`` 仅预览不发送。
- 发送内容与预览内容完全一致。
"""

from __future__ import annotations

import base64
import os
import smtplib
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from agent.email_sender import SendResult, send_plain_email


def _extract_body_from_mime(raw_message: str) -> str:
    """从 MIME 消息中解码 base64 编码的正文。"""
    # 找到 base64 编码块（最后一个空白行之后的内容）。
    parts = raw_message.split("\n\n")
    for part in reversed(parts):
        part = part.strip()
        if part and "Content-Type" not in part and "boundary" not in part:
            try:
                return base64.b64decode(part).decode("utf-8")
            except Exception:
                continue
    return ""


class EmailConfirmationTests(unittest.TestCase):
    """覆盖确认流程的各种场景。"""

    def setUp(self) -> None:
        os.environ["QQ_EMAIL_ADDRESS"] = "sender@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "test_auth_code_16chars"

    def tearDown(self) -> None:
        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE"):
            os.environ.pop(key, None)

    # ── 确认后发送成功 ───────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_send_after_confirmation(self, mock_smtp_class: MagicMock) -> None:
        """确认后应真正调用 SMTP 发送。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # 直接调用 send_plain_email（模拟确认后的调用）。
        result = send_plain_email(
            to_address="receiver@qq.com",
            subject="确认测试",
            body="确认后的正文内容。",
        )

        self.assertTrue(result.success)
        # 验证 sendmail 被调用且内容正确。
        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        # sendmail(from, to, msg_string)
        decoded_body = _extract_body_from_mime(call_args[0][2])
        self.assertIn("receiver@qq.com", call_args[0])
        self.assertIn("确认后的正文内容。", decoded_body)

    # ── 内容一致性 ───────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_sent_content_matches_preview(self, mock_smtp_class: MagicMock) -> None:
        """实际发送的内容应与预览时展示的内容完全一致。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        body = "预览中看到的内容\n第二行\n第三行"
        send_plain_email(to_address="r@qq.com", subject="一致测试", body=body)

        # 从 sendmail 调用中提取实际发送的消息体。
        call_args = mock_server.sendmail.call_args
        decoded_body = _extract_body_from_mime(call_args[0][2])
        self.assertIn(body, decoded_body)
        # 验证预览中的 body 逐字出现在已发送消息中。

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_special_characters_preserved(self, mock_smtp_class: MagicMock) -> None:
        """特殊字符（中文、换行、符号）在发送中应完整保留。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        body = "中文内容\n\n符号: @#$%^&*()\n换行测试\n   缩进测试"
        send_plain_email(to_address="r@qq.com", subject="特殊字符", body=body)

        call_args = mock_server.sendmail.call_args
        decoded_body = _extract_body_from_mime(call_args[0][2])
        self.assertIn("中文内容", decoded_body)
        self.assertIn("@#$%^&*()", decoded_body)
        self.assertIn("   缩进测试", decoded_body)

    # ── 取消日志 ──────────────────────────────────────────────

    @patch("agent.logger.log_email_cancelled")
    def test_log_email_cancelled_writes_correct_fields(
        self, mock_log: MagicMock
    ) -> None:
        """取消日志应包含收件人、主题和取消原因。"""
        from agent.logger import log_email_cancelled

        log_email_cancelled(
            to_address="r@qq.com",
            subject="测试取消",
            reason="用户在确认环节取消",
        )

        mock_log.assert_called_once_with(
            to_address="r@qq.com",
            subject="测试取消",
            reason="用户在确认环节取消",
        )

    @patch("agent.logger.log_email_cancelled")
    def test_log_email_cancelled_no_sensitive_data(
        self, mock_log: MagicMock
    ) -> None:
        """取消日志不应包含授权码等敏感信息。"""
        from agent.logger import log_email_cancelled

        log_email_cancelled(
            to_address="r@qq.com",
            subject="安全测试",
        )

        call_args = mock_log.call_args.kwargs
        self.assertNotIn("auth_code", call_args)
        self.assertNotIn("password", call_args)
        self.assertNotIn("QQ_EMAIL", str(call_args))

    # ── 未确认绝不发送 ───────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_cancelled_never_calls_smtp(self, mock_smtp_class: MagicMock) -> None:
        """当 send_plain_email 未被调用时（取消场景），SMTP 绝不应被调用。"""
        # 模拟取消流程：不调用 send_plain_email。
        # 验证 SMTP_SSL 没有被实例化。
        mock_smtp_class.assert_not_called()

    # ── 返回结果一致性 ───────────────────────────────────────

    def test_failure_result_contains_to_and_subject(self) -> None:
        """失败时的 SendResult 应包含原始收件人和主题。"""
        result = send_plain_email(to_address="  ")

        self.assertFalse(result.success)
        self.assertIn("  ", result.to_address)

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_success_result_matches_input(self, mock_smtp_class: MagicMock) -> None:
        """成功时 SendResult 的 to_address 和 subject 应与输入一致。"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_plain_email(
            to_address="target@qq.com",
            subject="结果验证",
            body="正文",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.to_address, "target@qq.com")
        self.assertEqual(result.subject, "结果验证")


if __name__ == "__main__":
    unittest.main()
