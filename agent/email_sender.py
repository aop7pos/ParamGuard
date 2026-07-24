"""使用 QQ 邮箱 SMTP 发送纯文本邮件（可附带安全目录内的附件）。

授权码通过 ``agent.config`` 从 ``.env`` 安全读取，
不会出现在代码、返回结果或日志中。附件只能来自 ``tests/`` 目录。
"""

from __future__ import annotations

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from os import PathLike
from pathlib import Path

from .config import load_qq_email_config, load_whitelist
from .tool_result import ErrorType, ToolResult, write_audit_log

# QQ 邮箱 SMTP 服务器配置。
_SMTP_HOST = "smtp.qq.com"
_SMTP_PORT = 465  # SSL

# 附件只允许来自该目录。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ALLOWED_DIR = _PROJECT_ROOT / "tests"


def _validate_attachment(path: str | PathLike[str]) -> tuple[Path, bytes, str]:
    """校验单个附件路径，返回 ``(解析路径, 内容字节, 文件名)``。

    校验规则：
    - 路径不能为空
    - 必须在 ``tests/`` 目录内
    - 必须是文件，不能是目录
    - 文件必须存在
    - 内容必须可读

    Raises:
        ValueError: 校验失败时抛出，包含明确原因。
    """
    if isinstance(path, str):
        if not path.strip():
            raise ValueError("附件路径不能为空")
        if "\0" in path:
            raise ValueError("附件路径包含非法字符（空字节）")
        file_path = Path(path)
    elif isinstance(path, PathLike):
        file_path = Path(path)
    else:
        raise ValueError("附件路径必须是字符串或路径对象")

    resolved = file_path.resolve()

    # 安全检查：必须在 tests/ 目录内。
    try:
        resolved.relative_to(_ALLOWED_DIR.resolve())
    except ValueError:
        raise ValueError(
            f"附件不在允许目录中（仅允许 tests/ 目录内的文件）: {file_path}"
        )

    if resolved.is_dir():
        raise ValueError(f"附件路径是目录，不是文件: {file_path}")

    if not resolved.is_file():
        raise ValueError(f"附件文件不存在: {file_path}")

    try:
        content = resolved.read_bytes()
    except OSError as exc:
        raise ValueError(f"无法读取附件: {exc}")

    return resolved, content, resolved.name


def send_plain_email(
    to_address: str = "1962383827@qq.com",
    *,
    subject: str = "ParamGuard 测试邮件",
    body: str = "这是一封来自 ParamGuard 项目的测试邮件。\n\n如果收到此邮件，说明 QQ 邮箱 SMTP 发送功能正常工作。\n",
    attachments: list[str | PathLike[str]] | None = None,
) -> ToolResult:
    """发送一封纯文本邮件，可附带安全目录内的附件。

    使用 ``.env`` 中配置的 QQ 邮箱作为发件人，通过 SSL 连接
    SMTP 服务器发送。所有错误均封装在返回值中，不抛出异常。

    附件只能来自项目 ``tests/`` 目录，任何越权路径（包括路径穿越）
    都会被拒绝。

    **敏感信息保护**：授权码绝不会出现在返回结果、日志或错误信息中。

    Args:
        to_address: 收件人邮箱地址。
        subject: 邮件主题。
        body: 邮件正文（纯文本）。
        attachments: 附件文件路径列表，可选。

    Returns:
        ``ToolResult``，包含统一的执行状态、参数、结果和审计信息。
    """
    if attachments is None:
        attachments = []

    orig_to_address = to_address  # 保留原始值用于结果（不做 strip）

    # 构造脱敏后的 params（不含授权码和正文内容）。
    safe_params: dict = {
        "to_address": orig_to_address,
        "subject": subject,
        "body_length": len(body),
        "attachment_count": len(attachments),
        "attachment_names": [Path(p).name for p in attachments],
    }

    def _make(
        *,
        success: bool,
        error: str = "",
        error_type: str = "",
        attachment_names: list[str] | None = None,
    ) -> ToolResult:
        tr = ToolResult(
            success=success,
            tool_name="send_email",
            params=safe_params,
            result={
                "to_address": orig_to_address,
                "subject": subject,
                "attachment_names": attachment_names or [],
            },
            error_type=error_type,
            error=error,
        )
        write_audit_log(tr)
        return tr

    # ── 参数校验 ──────────────────────────────────────────────
    if not to_address or not to_address.strip():
        return _make(
            success=False,
            error="收件人地址不能为空",
            error_type=ErrorType.VALIDATION,
        )

    to_address = to_address.strip()
    safe_params["to_address"] = to_address

    # ── 白名单检查（发送前最后一道防线） ─────────────────────
    whitelist = load_whitelist()
    if whitelist and to_address not in whitelist:
        return _make(
            success=False,
            error=f"收件人不在白名单中: {to_address}",
            error_type=ErrorType.WHITELIST,
        )

    # ── 附件校验（在构造邮件前验证所有附件） ─────────────────
    validated_attachments: list[tuple[str, bytes]] = []
    attachment_names: list[str] = []
    for att in attachments:
        try:
            _, content_bytes, filename = _validate_attachment(att)
            validated_attachments.append((filename, content_bytes))
            attachment_names.append(filename)
        except ValueError as exc:
            return _make(
                success=False,
                error=str(exc),
                error_type=ErrorType.ATTACHMENT,
            )

    # 加载发件人配置。
    try:
        config = load_qq_email_config()
    except ValueError as exc:
        return _make(
            success=False,
            error=str(exc),
            error_type=ErrorType.CONFIG,
        )

    # ── 构造邮件 ──────────────────────────────────────────────
    msg = MIMEMultipart()
    msg["From"] = config.email_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 添加附件（内容在确认时已校验，此处直接附加）。
    for filename, content_bytes in validated_attachments:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(content_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{filename}"',
        )
        msg.attach(part)

    # ── 发送邮件 ──────────────────────────────────────────────
    try:
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
            server.login(config.email_address, config.auth_code)
            server.sendmail(config.email_address, to_address, msg.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        # 注意：错误信息中不包含授权码本身。
        return _make(
            success=False,
            error=f"SMTP 认证失败，请检查邮箱地址和授权码是否正确",
            error_type=ErrorType.SMTP_AUTH,
        )
    except smtplib.SMTPException as exc:
        return _make(
            success=False,
            error=f"SMTP 发送失败: {exc}",
            error_type=ErrorType.SMTP,
        )
    except OSError as exc:
        return _make(
            success=False,
            error=f"网络连接失败: {exc}",
            error_type=ErrorType.NETWORK,
        )

    return _make(
        success=True,
        attachment_names=attachment_names,
    )
