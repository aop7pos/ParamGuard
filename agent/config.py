"""从项目根目录的 ``.env`` 文件中安全读取 QQ 邮箱配置。

真实凭据存储在 ``.env`` 中（已被 ``.gitignore`` 忽略），
``.env.example`` 仅保留字段名作为参考。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录，.env 文件所在位置。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"


@dataclass
class QQEmailConfig:
    """QQ 邮箱 SMTP 配置。

    Attributes:
        email_address: QQ 邮箱地址。
        auth_code: SMTP 授权码（非 QQ 密码）。
    """
    email_address: str
    auth_code: str


def _load_dotenv() -> None:
    """加载 .env 文件，文件不存在时不报错（由调用方校验）。"""
    load_dotenv(_ENV_PATH, override=False)


def _require_env(key: str) -> str:
    """读取必需的环境变量，缺失或为占位符时报错。"""
    value = os.getenv(key, "").strip()
    if not value:
        raise ValueError(
            f"缺少必需的环境变量: {key}"
            f"，请在 {_ENV_PATH} 中设置（参考 .env.example）"
        )
    # 防止误用示例占位符。
    if value.upper() in ("XXX", "XXXX", "YOUR_", "CHANGE_ME", "PLACEHOLDER"):
        raise ValueError(
            f"环境变量 {key} 仍为占位符，请在 {_ENV_PATH} 中填入真实凭据"
        )
    return value


def load_qq_email_config() -> QQEmailConfig:
    """加载 QQ 邮箱配置。

    Returns:
        ``QQEmailConfig``，包含邮箱地址和 SMTP 授权码。

    Raises:
        ValueError: 如果 ``.env`` 文件缺失、变量未设置或仍为占位符。
    """
    _load_dotenv()

    email_address = _require_env("QQ_EMAIL_ADDRESS")
    auth_code = _require_env("QQ_EMAIL_AUTH_CODE")

    return QQEmailConfig(email_address=email_address, auth_code=auth_code)
