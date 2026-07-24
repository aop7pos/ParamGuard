"""使用 QQ 邮箱 SMTP 发送纯文本邮件。

授权码通过 ``agent.config`` 从 ``.env`` 安全读取，
不会出现在代码中。
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .config import load_qq_email_config
from .logger import log_email_send

# QQ 邮箱 SMTP 服务器配置。
_SMTP_HOST = "smtp.qq.com"
_SMTP_PORT = 465  # SSL


@dataclass
class SendResult:
    """邮件发送的执行结果。

    Attributes:
        to_address: 收件人地址。
        subject: 邮件主题。
        success: 是否发送成功。
        error: 失败时的错误信息，成功时为空字符串。
    """
    to_address: str
    subject: str
    success: bool
    error: str


def send_plain_email(
    to_address: str = "1962383827@qq.com",
    *,
    subject: str = "ParamGuard 测试邮件",
    body: str = "这是一封来自 ParamGuard 项目的测试邮件。\n\n如果收到此邮件，说明 QQ 邮箱 SMTP 发送功能正常工作。\n",
) -> SendResult:
    """发送一封纯文本邮件。

    使用 ``.env`` 中配置的 QQ 邮箱作为发件人，通过 SSL 连接
    SMTP 服务器发送。所有错误均封装在返回值中，不抛出异常。

    Args:
        to_address: 收件人邮箱地址。
        subject: 邮件主题。
        body: 邮件正文（纯文本）。

    Returns:
        ``SendResult``，包含收件人、主题、成功标志和错误信息。
    """
    # ── 参数校验 ──────────────────────────────────────────────
    if not to_address or not to_address.strip():
        result = SendResult(to_address=to_address, subject=subject, success=False, error="收件人地址不能为空")
        log_email_send(to_address=result.to_address, subject=result.subject, success=result.success, error=result.error)
        return result

    to_address = to_address.strip()

    # 加载发件人配置。
    try:
        config = load_qq_email_config()
    except ValueError as exc:
        result = SendResult(to_address=to_address, subject=subject, success=False, error=str(exc))
        log_email_send(to_address=result.to_address, subject=result.subject, success=result.success, error=result.error)
        return result

    # ── 构造邮件 ──────────────────────────────────────────────
    msg = MIMEMultipart()
    msg["From"] = config.email_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # ── 发送邮件 ──────────────────────────────────────────────
    try:
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
            server.login(config.email_address, config.auth_code)
            server.sendmail(config.email_address, to_address, msg.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        result = SendResult(to_address=to_address, subject=subject, success=False, error=f"SMTP 认证失败，请检查邮箱地址和授权码: {exc}")
        log_email_send(to_address=result.to_address, subject=result.subject, success=result.success, error=result.error)
        return result
    except smtplib.SMTPException as exc:
        result = SendResult(to_address=to_address, subject=subject, success=False, error=f"SMTP 发送失败: {exc}")
        log_email_send(to_address=result.to_address, subject=result.subject, success=result.success, error=result.error)
        return result
    except OSError as exc:
        result = SendResult(to_address=to_address, subject=subject, success=False, error=f"网络连接失败: {exc}")
        log_email_send(to_address=result.to_address, subject=result.subject, success=result.success, error=result.error)
        return result

    result = SendResult(to_address=to_address, subject=subject, success=True, error="")
    log_email_send(to_address=result.to_address, subject=result.subject, success=result.success, error=result.error)
    return result
