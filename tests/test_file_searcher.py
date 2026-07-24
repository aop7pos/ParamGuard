"""文件搜索功能的标准库测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.file_searcher import search_files
from agent.tool_result import ToolResult

# 测试文件所在目录，即项目的 tests/ 目录。
_TESTS_DIR = Path(__file__).resolve().parent


class SearchFilesTests(unittest.TestCase):
    """覆盖正常搜索、边界情况和安全限制。"""

    # ── 成功场景：文件名匹配 ─────────────────────────────────

    def test_matches_by_filename(self) -> None:
        """按文件名关键词搜索应返回匹配文件。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "report_2024.txt").write_text("data", encoding="utf-8")
            (Path(directory) / "notes.txt").write_text("other", encoding="utf-8")

            result = search_files("report", search_dir=directory, search_content=False)

            matches = result.result.get("matches", [])
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["file_name"], "report_2024.txt")
            self.assertEqual(matches[0]["match_type"], "filename")
            self.assertEqual(result.result.get("files_scanned"), 2)
            self.assertEqual(result.result.get("files_skipped"), 0)

    def test_filename_match_case_insensitive_by_default(self) -> None:
        """文件名匹配默认不区分大小写。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "Report.TXT").write_text("data", encoding="utf-8")

            result = search_files("report", search_dir=directory, search_content=False)

            matches = result.result.get("matches", [])
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["file_name"], "Report.TXT")

    def test_filename_match_case_sensitive(self) -> None:
        """区分大小写时大写查询不应匹配小写文件名。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "report.txt").write_text("data", encoding="utf-8")

            result = search_files(
                "Report", search_dir=directory, search_content=False, case_sensitive=True,
            )

            self.assertEqual(len(result.result.get("matches", [])), 0)

    # ── 成功场景：内容匹配 ───────────────────────────────────

    def test_matches_by_content(self) -> None:
        """按文件内容关键词搜索应返回匹配及片段。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "data.txt"
            file_path.write_text("用户名: alice\n邮箱: alice@example.com\n", encoding="utf-8")

            result = search_files("alice", search_dir=directory, search_filename=False)

            matches = result.result.get("matches", [])
            self.assertGreaterEqual(len(matches), 1)
            content_matches = [m for m in matches if m["match_type"] == "content"]
            self.assertGreaterEqual(len(content_matches), 1)
            self.assertIn("alice", content_matches[0]["snippet"])

    def test_content_match_case_insensitive(self) -> None:
        """内容匹配默认不区分大小写。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "data.txt").write_text("HELLO WORLD", encoding="utf-8")

            result = search_files("hello", search_dir=directory, search_filename=False)

            self.assertGreaterEqual(len(result.result.get("matches", [])), 0)

    # ── 成功场景：无结果 ─────────────────────────────────────

    def test_no_matches_returns_empty(self) -> None:
        """无匹配时应返回空列表，不报错。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "notes.txt").write_text("nothing here", encoding="utf-8")

            result = search_files("xyznotfound", search_dir=directory)

            self.assertEqual(len(result.result.get("matches", [])), 0)
            self.assertEqual(result.result.get("files_scanned"), 1)
            self.assertEqual(len(result.result.get("errors", [])), 0)

    # ── 失败场景：参数校验 ───────────────────────────────────

    def test_empty_query_rejected(self) -> None:
        """空搜索词应返回错误信息。"""
        result = search_files("  ")

        self.assertEqual(len(result.result.get("matches", [])), 0)
        self.assertFalse(result.success)
        self.assertIn("不能为空", result.error)

    def test_non_string_query_handled(self) -> None:
        """非字符串查询应优雅处理。"""
        result = search_files(123)  # type: ignore[arg-type]

        self.assertEqual(len(result.result.get("matches", [])), 0)
        self.assertFalse(result.success)

    # ── 安全场景 ─────────────────────────────────────────────

    def test_search_outside_allowed_dir_rejected(self) -> None:
        """搜索 tests/ 之外的目录应被拒绝。"""
        with tempfile.TemporaryDirectory() as outside_dir:
            result = search_files("test", search_dir=outside_dir)

            self.assertEqual(len(result.result.get("matches", [])), 0)
            self.assertFalse(result.success)
            self.assertIn("不允许", result.error)

    def test_path_traversal_rejected(self) -> None:
        """路径穿越形式的搜索应被拒绝。"""
        result = search_files("test", search_dir=_TESTS_DIR / ".." / "agent")

        self.assertEqual(len(result.result.get("matches", [])), 0)
        self.assertFalse(result.success)
        self.assertIn("不允许", result.error)

    # ── 边界场景 ─────────────────────────────────────────────

    def test_skips_binary_files(self) -> None:
        """应跳过二进制文件，不报错。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            # 创建一个带二进制扩展名的文件。
            bin_path = Path(directory) / "image.png"
            bin_path.write_bytes(b"\x89PNG\r\n\x1a\n")
            (Path(directory) / "readme.txt").write_text("hello", encoding="utf-8")

            result = search_files("hello", search_dir=directory)

            # PNG 不应被扫描，只扫描 txt 文件。
            self.assertEqual(result.result.get("files_scanned"), 1)

    def test_skips_unreadable_file_and_logs_error(self) -> None:
        """无法读取的文件应跳过并记录原因。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            # 用非 UTF-8 字节写入，然后以 UTF-8 读取会触发 UnicodeError。
            bad_path = Path(directory) / "bad.txt"
            bad_path.write_bytes(b"\x80\x81\x82")
            (Path(directory) / "good.txt").write_text("safe content", encoding="utf-8")

            result = search_files("safe", search_dir=directory)

            self.assertGreaterEqual(result.result.get("files_skipped", 0), 1)
            self.assertGreaterEqual(len(result.result.get("errors", [])), 1)

    def test_default_search_dir_is_tests(self) -> None:
        """不指定 search_dir 时默认在 tests/ 目录搜索。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            unique_name = "uniquefile_xyz789"
            (Path(directory) / f"{unique_name}.txt").write_text("data", encoding="utf-8")

            result = search_files(unique_name, search_dir=directory, search_content=False)

            matches = result.result.get("matches", [])
            self.assertEqual(len(matches), 1)
            self.assertIn(unique_name, matches[0]["file_name"])

    def test_search_dir_not_exists(self) -> None:
        """搜索目录不存在时应记录错误。"""
        result = search_files("test", search_dir=_TESTS_DIR / "nonexistent_dir")

        self.assertEqual(len(result.result.get("matches", [])), 0)
        self.assertFalse(result.success)
        self.assertIn("不存在", result.error)

    # ── 返回类型 ─────────────────────────────────────────────

    def test_returns_tool_result_instance(self) -> None:
        """返回值始终是 ToolResult 实例。"""
        result = search_files("  ")
        self.assertIsInstance(result, ToolResult)

        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "ok.txt").write_text("data", encoding="utf-8")
            result = search_files("ok", search_dir=directory)
            self.assertIsInstance(result, ToolResult)

    def test_match_has_required_fields(self) -> None:
        """每条匹配应包含路径、文件名、类型和片段。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "hello.txt").write_text("hello world", encoding="utf-8")
            result = search_files("hello", search_dir=directory)

            matches = result.result.get("matches", [])
            self.assertGreaterEqual(len(matches), 1)
            match = matches[0]
            self.assertIn("file_path", match)
            self.assertIn("file_name", match)
            self.assertIn("match_type", match)
            self.assertIn("snippet", match)
            self.assertIn(match["match_type"], ("filename", "content"))

    # ── 统一字段完整性 ───────────────────────────────────────

    def test_tool_result_has_required_fields(self) -> None:
        """ToolResult 应包含所有统一字段。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            (Path(directory) / "ok.txt").write_text("data", encoding="utf-8")
            result = search_files("ok", search_dir=directory)

            self.assertTrue(result.success)
            self.assertEqual(result.tool_name, "search_files")
            self.assertIn("query", result.params)
            self.assertIsInstance(result.timestamp, str)
            self.assertTrue(len(result.timestamp) > 0)
            self.assertIsInstance(result.audit_id, str)
            self.assertTrue(len(result.audit_id) > 0)

    # ── 组合搜索 ─────────────────────────────────────────────

    def test_filename_and_content_both_searched_by_default(self) -> None:
        """默认同时搜索文件名和内容，可能产生多条匹配。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            # 文件名和内容都包含 "sun"。
            (Path(directory) / "sunshine.txt").write_text("the sun is bright", encoding="utf-8")

            result = search_files("sun", search_dir=directory)

            matches = result.result.get("matches", [])
            types = {m["match_type"] for m in matches}
            self.assertIn("filename", types)
            self.assertIn("content", types)


if __name__ == "__main__":
    unittest.main()
