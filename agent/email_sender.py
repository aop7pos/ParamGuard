"""使用 QQ 邮箱 SMTP 发送纯文本邮件（可附带安全目录内的附件）。

授权码通过 ``agent.config`` 从 ``.env`` 安全读取，
不会出现在代码中。附件只能来自 ``tests/`` 目录。
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from os import PathLike
from pathlib import Path

from .config import load_qq_email_config, load_whitelist
from .logger import log_email_send, log_email_rejected

# QQ 邮箱 SMTP 服务器配置。
_SMTP_HOST = "smtp.qq.com"
_SMTP_PORT = 465  # SSL

# 附件只允许来自该目录。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ALLOWED_DIR = _PROJECT_ROOT / "tests"


@dataclass
class SendResult:
    """邮件发送的执行结果。

    Attributes:
        to_address: 收件人地址。
        subject: 邮件主题。
        success: 是否发送成功。
        error: 失败时的错误信息，成功时为空字符串。
        attachment_names: 已发送的附件文件名列表。
    """
    to_address: str
    subject: str
    success: bool
    error: str
    attachment_names: list[str] = field(default_factory=list)


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
) -> SendResult:
    """发送一封纯文本邮件，可附带安全目录内的附件。

    使用 ``.env`` 中配置的 QQ 邮箱作为发件人，通过 SSL 连接
    SMTP 服务器发送。所有错误均封装在返回值中，不抛出异常。

    附件只能来自项目 ``tests/`` 目录，任何越权路径（包括路径穿越）
    都会被拒绝。

    Args:
        to_address: 收件人邮箱地址。
        subject: 邮件主题。
        body: 邮件正文（纯文本）。
        attachments: 附件文件路径列表，可选。

    Returns:
        ``SendResult``，包含收件人、主题、成功标志、错误信息
        和已发送的附件文件名。
    """
    if attachments is None:
        attachments = []

    # ── 参数校验 ──────────────────────────────────────────────
    if not to_address or not to_address.strip():
        result = SendResult(to_address=to_address, subject=subject, success=False, error="收件人地址不能为空")
        log_email_send(
            to_address=result.to_address, subject=result.subject,
            success=result.success, error=result.error,
            attachment_count=0, attachment_names=[],
        )
        return result

    to_address = to_address.strip()

    # ── 白名单检查（发送前最后一道防线） ─────────────────────
    whitelist = load_whitelist()
    if whitelist and to_address not in whitelist:
        result = SendResult(to_address=to_address, subject=subject, success=False,
            error=f"收件人不在白名单中: {to_address}")
        log_email_rejected(to_address=to_address, subject=subject, reason=result.error)
        return result

    # ── 附件校验（在构造邮件前验证所有附件） ─────────────────
    validated_attachments: list[tuple[str, bytes]] = []
    attachment_names: list[str] = []
    for att in attachments:
        try:
            _, content_bytes, filename = _validate_attachment(att)
            validated_attachments.append((filename, content_bytes))
            attachment_names.append(filename)
        except ValueError as exc:
            result = SendResult(to_address=to_address, subject=subject, success=False, error=str(exc))
            log_email_send(
                to_address=result.to_address, subject=result.subject,
                success=result.success, error=result.error,
                attachment_count=0, attachment_names=[],
            )
            return result

    # 加载发件人配置。
    try:
        config = load_qq_email_config()
    except ValueError as exc:
        result = SendResult(to_address=to_address, subject=subject, success=False, error=str(exc))
        log_email_send(
            to_address=result.to_address, subject=result.subject,
            success=result.success, error=result.error,
            attachment_count=0, attachment_names=[],
        )
        return result

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
        result = SendResult(to_address=to_address, subject=subject, success=False,
            error=f"SMTP 认证失败，请检查邮箱地址和授权码: {exc}")
        log_email_send(
            to_address=result.to_address, subject=result.subject,
            success=result.success, error=result.error,
            attachment_count=0, attachment_names=[],
        )
        return result
    except smtplib.SMTPException as exc:
        result = SendResult(to_address=to_address, subject=subject, success=False,
            error=f"SMTP 发送失败: {exc}")
        log_email_send(
            to_address=result.to_address, subject=result.subject,
            success=result.success, error=result.error,
            attachment_count=0, attachment_names=[],
        )
        return result
    except OSError as exc:
        result = SendResult(to_address=to_address, subject=subject, success=False,
            error=f"网络连接失败: {exc}")
        log_email_send(
            to_address=result.to_address, subject=result.subject,
            success=result.success, error=result.error,
            attachment_count=0, attachment_names=[],
        )
        return result

    result = SendResult(
        to_address=to_address, subject=subject, success=True, error="",
        attachment_names=attachment_names,
    )
    log_email_send(
        to_address=result.to_address, subject=result.subject,
        success=result.success, error=result.error,
        attachment_count=len(result.attachment_names),
        attachment_names=result.attachment_names,
    )
    return result
