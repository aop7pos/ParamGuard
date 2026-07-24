"""文件读取功能的标准库测试。"""

from pathlib import Path
import tempfile
import unittest

from agent.file_reader import read_file_content

# 测试文件所在目录，即项目的 tests/ 目录。
_TESTS_DIR = Path(__file__).resolve().parent


class ReadFileContentTests(unittest.TestCase):
    """覆盖正常读取和常见无效输入。"""

    def test_returns_complete_utf8_content(self) -> None:
        """应读取文件的完整 UTF-8 内容，包括换行符。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "content.txt"
            file_path.write_text("第一行\n第二行", encoding="utf-8")

            self.assertEqual(read_file_content(file_path), "第一行\n第二行")

    def test_accepts_string_path(self) -> None:
        """字符串路径应与 Path 路径得到相同结果。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            file_path = Path(directory) / "content.txt"
            file_path.write_text("hello", encoding="utf-8")

            self.assertEqual(read_file_content(str(file_path)), "hello")

    def test_raises_for_missing_file(self) -> None:
        """不存在的文件不能被静默忽略，并给出清晰的中文错误。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            missing_path = Path(directory) / "missing.txt"

            with self.assertRaisesRegex(FileNotFoundError, "文件不存在"):
                read_file_content(missing_path)

    def test_rejects_empty_path(self) -> None:
        """空白路径应给出清晰的参数错误。"""
        with self.assertRaisesRegex(ValueError, "不能为空"):
            read_file_content("  ")

    def test_rejects_directory(self) -> None:
        """目录不是文本文件，不能作为读取目标。"""
        with tempfile.TemporaryDirectory(dir=_TESTS_DIR) as directory:
            with self.assertRaisesRegex(ValueError, "目录"):
                read_file_content(directory)

    def test_rejects_path_outside_tests_dir(self) -> None:
        """不允许读取 tests/ 目录之外的文件。"""
        # 使用系统临时目录，一定不在 tests/ 内。
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_text("secret", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "不允许"):
                read_file_content(outside_file)

    def test_rejects_relative_path_escaping_tests_dir(self) -> None:
        """使用 .. 绕过 tests/ 目录的相对路径也应被拒绝。"""
        with self.assertRaisesRegex(ValueError, "不允许"):
            read_file_content(_TESTS_DIR / ".." / "agent" / "file_reader.py")


if __name__ == "__main__":
    unittest.main()
