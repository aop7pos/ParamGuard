"""文件读取功能的标准库测试。"""

from pathlib import Path
import tempfile
import unittest

from agent.file_reader import ReadResult, read_file_content

# 测试文件所在目录，即项目的 tests/ 目录。
_TESTS_DIR = Path(__file__).resolve().parent


class ReadFileContentTests(unittest.TestCase):
    """覆盖正常读取和常见无效输入。"""

    # ── 成功场景 ──────────────────────────────────────────────

    def test_returns_complete_utf8_content(self) -> None:
        """成功读取时应返回路径、内容和 success=True。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "content.txt"
            file_path.write_text("第一行\n第二行", encoding="utf-8")

            result = read_file_content(file_path)

            self.assertTrue(result.success)
            self.assertEqual(result.content, "第一行\n第二行")
            self.assertEqual(result.path, str(file_path.resolve()))
            self.assertEqual(result.error, "")

    def test_accepts_string_path(self) -> None:
        """字符串路径应与 Path 路径得到相同结果。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "content.txt"
            file_path.write_text("hello", encoding="utf-8")

            result = read_file_content(str(file_path))

            self.assertTrue(result.success)
            self.assertEqual(result.content, "hello")

    # ── 失败场景 ──────────────────────────────────────────────

    def test_fails_for_missing_file(self) -> None:
        """不存在的文件应返回 success=False 并包含清晰错误。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            missing_path = Path(directory) / "missing.txt"

            result = read_file_content(missing_path)

            self.assertFalse(result.success)
            self.assertIn("文件不存在", result.error)

    def test_fails_for_empty_path(self) -> None:
        """空白路径应返回清晰的参数错误。"""
        result = read_file_content("  ")

        self.assertFalse(result.success)
        self.assertIn("不能为空", result.error)

    def test_fails_for_null_byte_in_path(self) -> None:
        """路径中包含空字节（\0）属于非法输入，应被拦截。"""
        result = read_file_content("tests/good.txt\0hidden.txt")

        self.assertFalse(result.success)
        self.assertIn("非法字符", result.error)

    def test_fails_for_directory(self) -> None:
        """目录不是文本文件，不能作为读取目标。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            result = read_file_content(directory)

            self.assertFalse(result.success)
            self.assertIn("目录", result.error)

    def test_fails_for_path_outside_tests_dir(self) -> None:
        """不允许读取 tests/ 目录之外的文件。"""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_text("secret", encoding="utf-8")

            result = read_file_content(outside_file)

            self.assertFalse(result.success)
            self.assertIn("不允许", result.error)

    def test_fails_for_relative_path_escaping_tests_dir(self) -> None:
        """使用 .. 绕过 tests/ 目录的相对路径也应被拒绝。"""
        result = read_file_content(_TESTS_DIR / ".." / "agent" / "file_reader.py")

        self.assertFalse(result.success)
        self.assertIn("不允许", result.error)

    # ── 返回类型 ──────────────────────────────────────────────

    def test_returns_read_result_instance(self) -> None:
        """返回值始终是 ReadResult 实例。"""
        result = read_file_content("  ")
        self.assertIsInstance(result, ReadResult)

        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "ok.txt"
            file_path.write_text("data", encoding="utf-8")
            result = read_file_content(file_path)
            self.assertIsInstance(result, ReadResult)


if __name__ == "__main__":
    unittest.main()
