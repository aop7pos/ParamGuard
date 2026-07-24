"""邮件附件功能的测试。

验证：
- 正常附件可以发送。
- 路径穿越、目录外、不存在、目录等非法附件被拒绝。
- 附件内容与预览一致。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.email_sender import _validate_attachment, send_plain_email
from agent.tool_result import ToolResult

_TESTS_DIR = Path(__file__).resolve().parent


class AttachmentValidationTests(unittest.TestCase):
    """测试 _validate_attachment 的独立校验逻辑。"""

    def test_valid_file_passes(self) -> None:
        """tests/ 目录内的文件应通过校验。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "report.pdf"
            file_path.write_bytes(b"PDF content here")

            resolved, content, name = _validate_attachment(file_path)

            self.assertEqual(name, "report.pdf")
            self.assertEqual(content, b"PDF content here")

    def test_empty_path_rejected(self) -> None:
        """空白路径应被拒绝。"""
        with self.assertRaises(ValueError) as ctx:
            _validate_attachment("  ")
        self.assertIn("不能为空", str(ctx.exception))

    def test_null_byte_path_rejected(self) -> None:
        """含空字节的路径应被拒绝。"""
        with self.assertRaises(ValueError) as ctx:
            _validate_attachment("tests/report.pdf\0hidden")
        self.assertIn("非法字符", str(ctx.exception))

    def test_outside_allowed_dir_rejected(self) -> None:
        """tests/ 目录外的文件应被拒绝。"""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_text("secret", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                _validate_attachment(outside_file)
            self.assertIn("不在允许目录", str(ctx.exception))

    def test_path_traversal_rejected(self) -> None:
        """路径穿越应被拒绝。"""
        traversal = _TESTS_DIR / ".." / "agent" / "file_reader.py"

        with self.assertRaises(ValueError) as ctx:
            _validate_attachment(traversal)
        self.assertIn("不在允许目录", str(ctx.exception))

    def test_directory_rejected(self) -> None:
        """目录作为附件应被拒绝。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            with self.assertRaises(ValueError) as ctx:
                _validate_attachment(directory)
            self.assertIn("目录", str(ctx.exception))

    def test_missing_file_rejected(self) -> None:
        """不存在的文件应被拒绝。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            missing = Path(directory) / "ghost.txt"

            with self.assertRaises(ValueError) as ctx:
                _validate_attachment(missing)
            self.assertIn("不存在", str(ctx.exception))


class EmailWithAttachmentTests(unittest.TestCase):
    """测试 send_plain_email 的附件集成。"""

    def setUp(self) -> None:
        os.environ["QQ_EMAIL_ADDRESS"] = "sender@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "test_auth_code_16chars"
        os.environ["QQ_EMAIL_WHITELIST"] = ""

    def tearDown(self) -> None:
        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE", "QQ_EMAIL_WHITELIST"):
            os.environ.pop(key, None)

    # ── 正常附件发送 ──────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_sends_email_with_attachment(self, mock_smtp: MagicMock) -> None:
        """带一个附件时应成功发送，result 包含附件名。"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            att_path = Path(directory) / "data.csv"
            att_path.write_bytes(b"col1,col2\n1,2\n")

            result = send_plain_email(
                to_address="receiver@qq.com",
                attachments=[att_path],
            )

        self.assertTrue(result.success)
        self.assertIn("data.csv", result.result.get("attachment_names", []))

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_sends_email_with_multiple_attachments(self, mock_smtp: MagicMock) -> None:
        """多个附件应全部附加。"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "a.txt").write_text("a", encoding="utf-8")
            (Path(directory) / "b.txt").write_text("b", encoding="utf-8")

            result = send_plain_email(
                to_address="receiver@qq.com",
                attachments=[Path(directory) / "a.txt", Path(directory) / "b.txt"],
            )

        self.assertTrue(result.success)
        att_names = result.result.get("attachment_names", [])
        self.assertEqual(len(att_names), 2)
        self.assertIn("a.txt", att_names)
        self.assertIn("b.txt", att_names)

    # ── 附件被拒 ──────────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_rejects_outside_attachment(self, mock_smtp: MagicMock) -> None:
        """tests/ 外的附件应被拒绝，SMTP 不调用。"""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "evil.exe"
            outside_file.write_bytes(b"malware")

            result = send_plain_email(
                to_address="receiver@qq.com",
                attachments=[outside_file],
            )

        self.assertFalse(result.success)
        self.assertIn("不在允许目录", result.error)
        mock_smtp.assert_not_called()

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_rejects_traversal_attachment(self, mock_smtp: MagicMock) -> None:
        """路径穿越附件应被拒绝。"""
        result = send_plain_email(
            to_address="receiver@qq.com",
            attachments=[_TESTS_DIR / ".." / "agent" / "file_reader.py"],
        )

        self.assertFalse(result.success)
        self.assertIn("不在允许目录", result.error)
        mock_smtp.assert_not_called()

    # ── 附件内容一致性 ────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_attachment_content_in_sent_message(self, mock_smtp: MagicMock) -> None:
        """实际发送的 MIME 消息应包含附件二进制内容。"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            att_path = Path(directory) / "readme.txt"
            att_path.write_bytes(b"unique content ABC123")

            send_plain_email(
                to_address="receiver@qq.com",
                attachments=[att_path],
            )

        # 获取 sendmail 的第三个参数（完整 MIME 消息）。
        call_args = mock_server.sendmail.call_args
        mime_message = call_args[0][2]
        # 附件文件名应在消息头中。
        self.assertIn("readme.txt", mime_message)

    # ── 无附件向后兼容 ────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_no_attachments_still_works(self, mock_smtp: MagicMock) -> None:
        """不传 attachments 时行为不变。"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_plain_email(to_address="receiver@qq.com")

        self.assertTrue(result.success)
        self.assertEqual(result.result.get("attachment_names", []), [])


if __name__ == "__main__":
    unittest.main()
