"""ParamGuard Agent 的测试。

覆盖意图解析、工具调度、邮件确认流程、上下文管理和安全边界。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.agent import ParamGuardAgent, AgentContext, PlanStep, StepKind
from agent.tool_result import ToolResult

_TESTS_DIR = Path(__file__).resolve().parent


def _extract_body_from_mime(raw_message: str) -> str:
    """从 MIME 消息中解码 base64 编码的正文。"""
    import base64
    parts = raw_message.split("\n\n")
    for part in reversed(parts):
        part = part.strip()
        if part and "Content-Type" not in part and "boundary" not in part:
            try:
                return base64.b64decode(part).decode("utf-8")
            except Exception:
                continue
    return ""


class AgentIntentParsingTests(unittest.TestCase):
    """测试自然语言意图解析。"""

    def setUp(self):
        self.agent = ParamGuardAgent()

    # ── 搜索意图 ──────────────────────────────────────────────

    def test_parses_search_by_keyword(self):
        """包含"搜索"关键词应解析为 SEARCH 意图。"""
        plan = self.agent._parse_request('搜索"测试报告"的文件')
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].kind, StepKind.SEARCH)
        self.assertEqual(plan[0].params["query"], "测试报告")

    def test_parses_search_by_find(self):
        """"查找"也可以触发搜索。"""
        plan = self.agent._parse_request("查找日志文件")
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0].kind, StepKind.SEARCH)

    def test_parses_search_with_chinese_quotes(self):
        """中文引号内的内容应正确提取。"""
        plan = self.agent._parse_request('搜索"测试报告"文件')
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0].params["query"], "测试报告")

    # ── 读取意图 ──────────────────────────────────────────────

    def test_parses_read_by_filename(self):
        """包含完整路径应解析为 READ 意图。"""
        plan = self.agent._parse_request("读取 tests/demo.txt 文件")
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0].kind, StepKind.READ)
        self.assertIn("demo.txt", plan[0].params["path"])

    def test_parses_read_with_view_keyword(self):
        """"查看"也可以触发读取。"""
        plan = self.agent._parse_request("查看 tests/demo.txt")
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0].kind, StepKind.READ)

    # ── 邮件意图 ──────────────────────────────────────────────

    def test_parses_email_draft(self):
        """"整理成邮件草稿"应解析为 EMAIL 意图。"""
        plan = self.agent._parse_request(
            '把内容整理成邮件草稿，主题"测试"，发给 test@qq.com'
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0].kind, StepKind.EMAIL)

    def test_parses_email_with_recipient_and_subject(self):
        """应正确提取收件人和主题。"""
        plan = self.agent._parse_request(
            '发邮件给 user@qq.com，主题"日报通知"'
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0].params.get("to_address"), "user@qq.com")
        self.assertEqual(plan[0].params.get("subject"), "日报通知")

    # ── 无法识别 ──────────────────────────────────────────────

    def test_unknown_request_returns_none(self):
        """无法理解的请求应返回 None。"""
        plan = self.agent._parse_request("今天天气怎么样")
        self.assertIsNone(plan)

    def test_empty_request_returns_none(self):
        """空请求应返回 None。"""
        plan = self.agent._parse_request("")
        self.assertIsNone(plan)

    # ── 管道（多步骤） ────────────────────────────────────────

    def test_parses_search_and_email_pipeline(self):
        """同时包含搜索和邮件关键词时应产生多步骤计划。"""
        plan = self.agent._parse_request(
            '搜索"报告"然后发给 admin@qq.com，主题"日报"'
        )
        self.assertIsNotNone(plan)
        kinds = [s.kind for s in plan]
        self.assertIn(StepKind.SEARCH, kinds)
        self.assertIn(StepKind.EMAIL, kinds)


class AgentStepExecutionTests(unittest.TestCase):
    """测试工具调用和管道执行。"""

    def setUp(self):
        self.agent = ParamGuardAgent()

    # ── 搜索执行 ──────────────────────────────────────────────

    def test_search_execution_returns_tool_result(self):
        """搜索应返回有效的 ToolResult。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "report.txt").write_text("test data", encoding="utf-8")

            result = self.agent.run(f'搜索"report"的文件')

            self.assertIsInstance(result, ToolResult)
            self.assertEqual(result.tool_name, "search_files")
            self.assertIn("audit_id", result.__dict__)
            self.assertIn("timestamp", result.__dict__)

    def test_search_updates_context(self):
        """搜索后上下文应记录搜索结果。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "hello.txt").write_text("data", encoding="utf-8")

            self.agent.run(f'搜索"hello"的文件')
            ctx = self.agent.context

            self.assertIsNotNone(ctx.last_search_result)
            self.assertEqual(ctx.last_search_result.tool_name, "search_files")

    # ── 读取执行 ──────────────────────────────────────────────

    def test_read_execution_returns_tool_result(self):
        """读取应返回有效的 ToolResult。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "data.txt"
            file_path.write_text("hello world", encoding="utf-8")

            result = self.agent.run(f"读取 {file_path}")

            self.assertIsInstance(result, ToolResult)
            self.assertEqual(result.tool_name, "read_file")

    def test_read_updates_context(self):
        """读取后上下文应记录读取结果。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "data.txt"
            file_path.write_text("content here", encoding="utf-8")

            self.agent.run(f"读取 {file_path}")
            ctx = self.agent.context

            self.assertIsNotNone(ctx.last_read_result)
            self.assertEqual(ctx.last_read_result.tool_name, "read_file")
            self.assertIn("content here", ctx.last_read_result.result.get("content", ""))

    # ── 上下文引用式读取 ─────────────────────────────────────

    def test_reference_read_uses_search_context(self):
        """"读取第1个结果"应从上次搜索结果中选取。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            import uuid
            unique = uuid.uuid4().hex[:12]
            file_path = Path(directory) / f"ref_{unique}.txt"
            file_path.write_text(unique, encoding="utf-8")

            # 先搜索建立上下文。
            self.agent.run(f'搜索"{unique}"的文件')
            # 再引用式读取。
            result = self.agent.run("读取第1个结果")

            self.assertEqual(result.tool_name, "read_file")
            self.assertIn(f"ref_{unique}.txt", result.result.get("path", ""))

    # ── 重置 ──────────────────────────────────────────────────

    def test_reset_clears_context(self):
        """重置应清空所有上下文。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "data.txt"
            file_path.write_text("data", encoding="utf-8")

            self.agent.run(f"读取 {file_path}")
            self.agent.reset()

            ctx = self.agent.context
            self.assertIsNone(ctx.last_search_result)
            self.assertIsNone(ctx.last_read_result)
            self.assertIsNone(ctx.last_email_draft)


class AgentEmailConfirmationTests(unittest.TestCase):
    """测试邮件确认流程的安全边界。"""

    def setUp(self):
        os.environ["QQ_EMAIL_ADDRESS"] = "sender@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "test_auth_code_16chars"
        os.environ["QQ_EMAIL_WHITELIST"] = ""

    def tearDown(self):
        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE", "QQ_EMAIL_WHITELIST"):
            os.environ.pop(key, None)

    # ── 确认后发送 ────────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_email_sends_when_confirmed(self, mock_smtp):
        """用户确认后应真正发送邮件。"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # 使用始终返回 True 的确认回调。
        agent = ParamGuardAgent(confirm_fn=lambda draft: True)

        result = agent.run(
            '发邮件给 receiver@qq.com，主题"测试"'
        )

        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, "send_email")
        mock_server.sendmail.assert_called_once()

    # ── 拒绝后不发 ────────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_email_never_sends_when_denied(self, mock_smtp):
        """用户拒绝后绝不应调用 SMTP。"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # 使用始终返回 False 的确认回调。
        agent = ParamGuardAgent(confirm_fn=lambda draft: False)

        result = agent.run(
            '发邮件给 receiver@qq.com，主题"测试"'
        )

        self.assertFalse(result.success)
        self.assertIn("取消", result.error)
        # SMTP 绝不应被调用。
        mock_server.sendmail.assert_not_called()

    # ── 拒绝后仍有审计日志 ────────────────────────────────────

    @patch("agent.agent.write_audit_log")
    def test_denied_email_still_audited(self, mock_audit):
        """用户拒绝后应写入审计日志。"""
        agent = ParamGuardAgent(confirm_fn=lambda draft: False)

        agent.run('发邮件给 receiver@qq.com，主题"测试"')

        mock_audit.assert_called()
        tr = mock_audit.call_args[0][0]
        self.assertFalse(tr.success)
        self.assertIn("取消", tr.error)

    # ── 邮件使用上次读取的内容 ────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_email_uses_last_read_content(self, mock_smtp):
        """邮件正文应自动使用上次读取的文件内容。"""
        import base64
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        agent = ParamGuardAgent(confirm_fn=lambda draft: True)

        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "report.txt"
            file_path.write_text("这是报告内容", encoding="utf-8")

            # 先读取文件。
            agent.run(f"读取 {file_path}")
            # 再发送邮件（应使用读取的内容）。
            agent.run('发邮件给 r@qq.com，主题"报告"')

            # 从 MIME 消息中提取并解码正文。
            raw_message = mock_server.sendmail.call_args[0][2]
            # 正文是 base64 编码的，找到编码块并解码。
            decoded = _extract_body_from_mime(raw_message)
            self.assertIn("这是报告内容", decoded)

    # ── 无确认回调时使用内置确认 ──────────────────────────────

    def test_builtin_confirm_uses_input(self):
        """无自定义回调时应使用 input()。"""
        agent = ParamGuardAgent()

        with patch("builtins.input", return_value="yes"):
            confirmed = agent._request_confirmation({
                "to_address": "test@qq.com",
                "subject": "test",
                "body": "test body",
            })
        self.assertTrue(confirmed)

    def test_builtin_confirm_denies_on_no(self):
        """输入 'no' 时应拒绝。"""
        agent = ParamGuardAgent()

        with patch("builtins.input", return_value="no"):
            confirmed = agent._request_confirmation({
                "to_address": "test@qq.com",
                "subject": "test",
                "body": "test body",
            })
        self.assertFalse(confirmed)

    # ── 安全：Agent 不绕过底层限制 ────────────────────────────

    def test_agent_does_not_bypass_whitelist(self):
        """Agent 不应绕过低层的白名单检查。"""
        os.environ["QQ_EMAIL_WHITELIST"] = "allowed@qq.com"
        agent = ParamGuardAgent(confirm_fn=lambda draft: True)

        result = agent.run('发邮件给 hacker@evil.com，主题"test"')

        self.assertFalse(result.success)
        self.assertIn("不在白名单中", result.error)

    # ── 默认收件人 ────────────────────────────────────────────

    @patch("agent.email_sender.smtplib.SMTP_SSL")
    def test_email_uses_default_recipient(self, mock_smtp):
        """未指定收件人时使用默认地址。"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        agent = ParamGuardAgent(confirm_fn=lambda draft: True)

        agent.run('发邮件，主题"test"')

        mock_server.sendmail.assert_called_once()
        # 默认收件人应为 1962383827@qq.com。
        self.assertIn("1962383827@qq.com", mock_server.sendmail.call_args[0])


class AgentErrorHandlingTests(unittest.TestCase):
    """测试 Agent 的错误处理。"""

    def setUp(self):
        self.agent = ParamGuardAgent()

    def test_unknown_request_gives_helpful_error(self):
        """无法理解的请求应返回有帮助的错误信息。"""
        result = self.agent.run("今天天气怎么样")
        self.assertFalse(result.success)
        self.assertIn("无法理解", result.error)

    def test_empty_request_gives_error(self):
        """空请求应返回错误。"""
        result = self.agent.run("  ")
        self.assertFalse(result.success)

    def test_read_nonexistent_file_gives_error(self):
        """读取不存在的文件应返回错误（不崩溃）。"""
        result = self.agent.run("读取 tests/ghost_file_xyz.txt")
        self.assertFalse(result.success)
        self.assertIn("不存在", result.error)


class AgentAuditLoggingTests(unittest.TestCase):
    """测试 Agent 所有操作的审计日志记录。"""

    def setUp(self):
        self.agent = ParamGuardAgent()

    @patch("agent.file_searcher.write_audit_log")
    def test_search_is_audited(self, mock_audit):
        """搜索操作应写入审计日志。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "data.txt").write_text("test", encoding="utf-8")
            self.agent.run(f'搜索"data"的文件')

        mock_audit.assert_called()
        tr = mock_audit.call_args[0][0]
        self.assertEqual(tr.tool_name, "search_files")
        self.assertIn("audit_id", tr.__dict__)

    @patch("agent.file_reader.write_audit_log")
    def test_read_is_audited(self, mock_audit):
        """读取操作应写入审计日志。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "data.txt"
            file_path.write_text("test", encoding="utf-8")

            self.agent.run(f"读取 {file_path}")

        mock_audit.assert_called()
        tr = mock_audit.call_args[0][0]
        self.assertEqual(tr.tool_name, "read_file")

    @patch("agent.email_sender.write_audit_log")
    def test_email_is_audited(self, mock_audit):
        """邮件发送（确认后）应写入审计日志。"""
        os.environ["QQ_EMAIL_ADDRESS"] = "s@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "abcd1234abcd1234"
        os.environ["QQ_EMAIL_WHITELIST"] = ""

        agent = ParamGuardAgent(confirm_fn=lambda draft: True)
        result = agent.run('发邮件给 r@qq.com，主题"审计测试"')

        mock_audit.assert_called()
        tr = mock_audit.call_args[0][0]
        self.assertEqual(tr.tool_name, "send_email")
        # 确保敏感信息不在日志参数中。
        self.assertNotIn("auth_code", tr.params)

        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE", "QQ_EMAIL_WHITELIST"):
            os.environ.pop(key, None)


if __name__ == "__main__":
    unittest.main()
