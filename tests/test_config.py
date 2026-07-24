"""QQ 邮箱配置加载的测试。

验证：
- 有效配置可以正确加载。
- 缺失变量时抛出明确错误。
- 占位符值被拒绝。
- ``.env`` 已被 ``.gitignore`` 忽略。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.config import QQEmailConfig, load_qq_email_config

# 指向实际 .env 的路径，用于验证 gitignore。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
_GITIGNORE_PATH = _PROJECT_ROOT / ".gitignore"


class QQEmailConfigTests(unittest.TestCase):
    """覆盖配置加载的各种场景。"""

    def setUp(self) -> None:
        """每个测试前清除相关环境变量，避免交叉污染。"""
        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE"):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        """测试后清理。"""
        for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_AUTH_CODE"):
            os.environ.pop(key, None)

    # ── 成功场景 ──────────────────────────────────────────────

    def test_loads_valid_config(self) -> None:
        """设置有效环境变量后应成功加载 QQEmailConfig。"""
        os.environ["QQ_EMAIL_ADDRESS"] = "testuser@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "abcdefghijklmnop"

        config = load_qq_email_config()

        self.assertIsInstance(config, QQEmailConfig)
        self.assertEqual(config.email_address, "testuser@qq.com")
        self.assertEqual(config.auth_code, "abcdefghijklmnop")

    # ── 失败场景：缺失变量 ───────────────────────────────────

    @patch("agent.config.load_dotenv")
    def test_raises_when_email_missing(self, mock_load: MagicMock) -> None:
        """缺少邮箱地址时应抛出 ValueError。"""
        os.environ["QQ_EMAIL_AUTH_CODE"] = "abcdefghijklmnop"
        # 故意不设置 QQ_EMAIL_ADDRESS。

        with self.assertRaises(ValueError) as ctx:
            load_qq_email_config()
        self.assertIn("QQ_EMAIL_ADDRESS", str(ctx.exception))

    @patch("agent.config.load_dotenv")
    def test_raises_when_auth_code_missing(self, mock_load: MagicMock) -> None:
        """缺少授权码时应抛出 ValueError。"""
        os.environ["QQ_EMAIL_ADDRESS"] = "testuser@qq.com"
        # 故意不设置 QQ_EMAIL_AUTH_CODE。

        with self.assertRaises(ValueError) as ctx:
            load_qq_email_config()
        self.assertIn("QQ_EMAIL_AUTH_CODE", str(ctx.exception))

    @patch("agent.config.load_dotenv")
    def test_raises_when_both_missing(self, mock_load: MagicMock) -> None:
        """两个变量都缺失时应抛出 ValueError。"""
        with self.assertRaises(ValueError) as ctx:
            load_qq_email_config()
        self.assertIn("QQ_EMAIL_ADDRESS", str(ctx.exception))

    # ── 失败场景：占位符 ─────────────────────────────────────

    def test_rejects_placeholder_xxx(self) -> None:
        """变量值为 XXX 占位符时应被拒绝。"""
        os.environ["QQ_EMAIL_ADDRESS"] = "XXX"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "realcode1234567890"

        with self.assertRaises(ValueError) as ctx:
            load_qq_email_config()
        self.assertIn("占位符", str(ctx.exception))

    def test_rejects_placeholder_xxxx(self) -> None:
        """变量值为 XXXX 占位符时应被拒绝。"""
        os.environ["QQ_EMAIL_ADDRESS"] = "test@qq.com"
        os.environ["QQ_EMAIL_AUTH_CODE"] = "XXXX"

        with self.assertRaises(ValueError) as ctx:
            load_qq_email_config()
        self.assertIn("占位符", str(ctx.exception))

    # ── 安全验证 ─────────────────────────────────────────────

    def test_dotenv_is_in_gitignore(self) -> None:
        """验证 .env 已被 .gitignore 忽略。"""
        self.assertTrue(
            _GITIGNORE_PATH.exists(),
            ".gitignore 文件不存在",
        )
        gitignore_content = _GITIGNORE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            ".env",
            gitignore_content,
            ".gitignore 中未包含 .env 规则",
        )

    def test_dotenv_file_exists(self) -> None:
        """验证 .env 文件存在于项目根目录（含占位符凭据）。"""
        self.assertTrue(
            _ENV_PATH.exists(),
            ".env 文件不存在于项目根目录",
        )

    def test_dotenv_example_exists(self) -> None:
        """验证 .env.example 模板文件存在。"""
        example_path = _PROJECT_ROOT / ".env.example"
        self.assertTrue(
            example_path.exists(),
            ".env.example 模板文件不存在",
        )
        content = example_path.read_text(encoding="utf-8")
        self.assertIn("QQ_EMAIL_ADDRESS", content)
        self.assertIn("QQ_EMAIL_AUTH_CODE", content)


if __name__ == "__main__":
    unittest.main()
