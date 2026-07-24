"""文件读取日志记录功能的测试。

验证每次 ``read_file_content`` 调用后，日志文件中都会正确记录：
- 时间戳
- 文件路径
- 是否成功
- 失败原因（如有）
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent.file_reader import read_file_content
from agent.logger import _log_file_path

# 测试文件所在目录，即项目的 tests/ 目录。
_TESTS_DIR = Path(__file__).resolve().parent


def _read_last_log_entry() -> dict | None:
    """读取日志文件的最后一条记录并解析为字典。"""
    log_path = _log_file_path()
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return None
    return json.loads(lines[-1])


class LogFileReadTests(unittest.TestCase):
    """验证日志记录的正确性，覆盖成功与各种失败场景。"""

    # ── 辅助方法 ──────────────────────────────────────────────

    def _assert_log_entry(self, *, success: bool, path_contains: str, error_contains: str = "") -> None:
        """读取最新日志条目并校验各字段。"""
        entry = _read_last_log_entry()
        self.assertIsNotNone(entry, "日志文件应包含至少一条记录")
        self.assertIn("timestamp", entry, "日志条目缺少 timestamp 字段")
        self.assertIn("path", entry, "日志条目缺少 path 字段")
        self.assertIn("success", entry, "日志条目缺少 success 字段")
        self.assertIn("error", entry, "日志条目缺少 error 字段")

        self.assertEqual(entry["success"], success)
        self.assertIn(path_contains, entry["path"])
        if error_contains:
            self.assertIn(error_contains, entry["error"])

    # ── 场景 1：正常读取文件 ─────────────────────────────────

    def test_logs_successful_read(self) -> None:
        """成功读取文件后，日志应记录 success=true、路径和空 error。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "hello.txt"
            file_path.write_text("Hello, ParamGuard!", encoding="utf-8")

            read_file_content(file_path)

            self._assert_log_entry(
                success=True,
                path_contains="hello.txt",
            )
            entry = _read_last_log_entry()
            self.assertEqual(entry["error"], "")

    # ── 场景 2：文件不存在 ───────────────────────────────────

    def test_logs_missing_file(self) -> None:
        """文件不存在时，日志应记录 success=false 和原因。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            missing_path = Path(directory) / "ghost.txt"

            read_file_content(missing_path)

            self._assert_log_entry(
                success=False,
                path_contains="ghost.txt",
                error_contains="文件不存在",
            )

    # ── 场景 3：路径为空 ─────────────────────────────────────

    def test_logs_empty_path(self) -> None:
        """空白路径时，日志应记录 success=false 和原因。"""
        read_file_content("  ")

        self._assert_log_entry(
            success=False,
            path_contains="",
            error_contains="不能为空",
        )

    # ── 场景 4：尝试读取允许目录之外的文件 ───────────────────

    def test_logs_path_outside_allowed_dir(self) -> None:
        """访问 tests/ 之外的文件时，日志应记录拒绝原因。"""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_text("classified", encoding="utf-8")

            read_file_content(outside_file)

            self._assert_log_entry(
                success=False,
                path_contains="secret.txt",
                error_contains="不允许",
            )

    # ── 场景 5：使用路径穿越形式读取其他文件 ─────────────────

    def test_logs_path_traversal_attempt(self) -> None:
        """使用 .. 进行路径穿越时，日志应记录拒绝原因。"""
        traversal_path = _TESTS_DIR / ".." / "agent" / "file_reader.py"

        read_file_content(traversal_path)

        self._assert_log_entry(
            success=False,
            path_contains="file_reader.py",
            error_contains="不允许",
        )

    # ── 场景 6：目录作为读取目标 ─────────────────────────────

    def test_logs_directory_instead_of_file(self) -> None:
        """目标为目录时，日志应记录明确的目录错误。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            read_file_content(directory)

            self._assert_log_entry(
                success=False,
                path_contains=Path(directory).name,
                error_contains="目录",
            )

    # ── 场景 7：路径包含空字节（非法字符） ──────────────────

    def test_logs_null_byte_in_path(self) -> None:
        """路径包含空字节时，日志应记录非法字符错误。"""
        read_file_content("tests/data.txt\0hidden.txt")

        self._assert_log_entry(
            success=False,
            path_contains="tests/data.txt",
            error_contains="非法字符",
        )


if __name__ == "__main__":
    unittest.main()
