"""统一审计日志记录功能的测试。

验证每次工具调用后，审计日志文件中都会正确记录：
- 时间戳
- 审计编号
- 工具名称
- 参数
- 是否成功
- 错误类型
- 失败原因（如有）
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent.file_reader import read_file_content
from agent.tool_result import _audit_log_path

# 测试文件所在目录，即项目的 tests/ 目录。
_TESTS_DIR = Path(__file__).resolve().parent


def _read_last_audit_entry() -> dict | None:
    """读取统一审计日志文件的最后一条记录并解析为字典。"""
    log_path = _audit_log_path()
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return None
    return json.loads(lines[-1])


class LogFileReadTests(unittest.TestCase):
    """验证审计日志记录的正确性，覆盖成功与各种失败场景。"""

    # ── 辅助方法 ──────────────────────────────────────────────

    def _assert_log_entry(self, *, success: bool, error_contains: str = "",
                          error_type: str = "") -> None:
        """读取最新审计日志条目并校验各字段。"""
        entry = _read_last_audit_entry()
        self.assertIsNotNone(entry, "审计日志文件应包含至少一条记录")
        self.assertIn("audit_id", entry, "审计日志缺少 audit_id 字段")
        self.assertIn("timestamp", entry, "审计日志缺少 timestamp 字段")
        self.assertIn("tool_name", entry, "审计日志缺少 tool_name 字段")
        self.assertIn("success", entry, "审计日志缺少 success 字段")
        self.assertIn("params", entry, "审计日志缺少 params 字段")
        self.assertIn("result_summary", entry, "审计日志缺少 result_summary 字段")
        self.assertIn("error_type", entry, "审计日志缺少 error_type 字段")
        self.assertIn("error", entry, "审计日志缺少 error 字段")

        self.assertEqual(entry["success"], success)
        self.assertEqual(entry["tool_name"], "read_file")
        if error_contains:
            self.assertIn(error_contains, entry["error"])
        if error_type:
            self.assertEqual(entry["error_type"], error_type)

    # ── 场景 1：正常读取文件 ─────────────────────────────────

    def test_logs_successful_read(self) -> None:
        """成功读取文件后，审计日志应记录 success=true。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "hello.txt"
            file_path.write_text("Hello, ParamGuard!", encoding="utf-8")

            read_file_content(file_path)

            self._assert_log_entry(success=True)
            entry = _read_last_audit_entry()
            self.assertEqual(entry["error"], "")
            self.assertEqual(entry["error_type"], "")
            # 摘要应包含路径和内容长度。
            self.assertIn("path", entry["result_summary"])
            self.assertIn("content_length", entry["result_summary"])

    # ── 场景 2：文件不存在 ───────────────────────────────────

    def test_logs_missing_file(self) -> None:
        """文件不存在时，审计日志应记录 success=false 和原因。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            missing_path = Path(directory) / "ghost.txt"

            read_file_content(missing_path)

            self._assert_log_entry(
                success=False,
                error_contains="文件不存在",
                error_type="system",
            )

    # ── 场景 3：路径为空 ─────────────────────────────────────

    def test_logs_empty_path(self) -> None:
        """空白路径时，审计日志应记录 success=false 和原因。"""
        read_file_content("  ")

        self._assert_log_entry(
            success=False,
            error_contains="不能为空",
            error_type="validation",
        )

    # ── 场景 4：尝试读取允许目录之外的文件 ───────────────────

    def test_logs_path_outside_allowed_dir(self) -> None:
        """访问 tests/ 之外的文件时，审计日志应记录拒绝原因。"""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_text("classified", encoding="utf-8")

            read_file_content(outside_file)

            self._assert_log_entry(
                success=False,
                error_contains="不允许",
                error_type="permission",
            )

    # ── 场景 5：使用路径穿越形式读取其他文件 ─────────────────

    def test_logs_path_traversal_attempt(self) -> None:
        """使用 .. 进行路径穿越时，审计日志应记录拒绝原因。"""
        traversal_path = _TESTS_DIR / ".." / "agent" / "file_reader.py"

        read_file_content(traversal_path)

        self._assert_log_entry(
            success=False,
            error_contains="不允许",
            error_type="permission",
        )

    # ── 场景 6：目录作为读取目标 ─────────────────────────────

    def test_logs_directory_instead_of_file(self) -> None:
        """目标为目录时，审计日志应记录明确的目录错误。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            read_file_content(directory)

            self._assert_log_entry(
                success=False,
                error_contains="目录",
                error_type="validation",
            )

    # ── 场景 7：路径包含空字节（非法字符） ──────────────────

    def test_logs_null_byte_in_path(self) -> None:
        """路径包含空字节时，审计日志应记录非法字符错误。"""
        read_file_content("tests/data.txt\0hidden.txt")

        self._assert_log_entry(
            success=False,
            error_contains="非法字符",
            error_type="validation",
        )

    # ── 场景 8：审计记录唯一性 ───────────────────────────────

    def test_audit_id_is_unique(self) -> None:
        """每次操作的 audit_id 应各不相同。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "a.txt"
            file_path.write_text("data", encoding="utf-8")

            result1 = read_file_content(file_path)
            result2 = read_file_content(file_path)

            self.assertNotEqual(result1.audit_id, result2.audit_id)

    # ── 场景 9：日志不含敏感信息 ─────────────────────────────

    def test_audit_log_no_sensitive_data(self) -> None:
        """审计日志不应包含任何敏感信息。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "ok.txt"
            file_path.write_text("data", encoding="utf-8")

            read_file_content(file_path)

        entry = _read_last_audit_entry()
        # 确保日志中不包含敏感字段。
        entry_str = json.dumps(entry)
        self.assertNotIn("auth_code", entry_str.lower())
        self.assertNotIn("password", entry_str.lower())
        self.assertNotIn("QQ_EMAIL_AUTH_CODE", entry_str)


if __name__ == "__main__":
    unittest.main()
