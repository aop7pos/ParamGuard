"""文件读取操作的日志记录模块。

每条日志以 JSON 行格式写入 ``logs/`` 目录，记录：
- 时间戳
- 读取的文件路径
- 是否成功
- 失败原因（如有）
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

# 项目根目录与日志目录。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"
# 保证多线程下的写入安全。
_LOCK = threading.Lock()


def _ensure_logs_dir() -> None:
    """确保日志目录存在。"""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _log_file_path() -> Path:
    """返回当天的日志文件路径，按日期分文件便于管理和归档。"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _LOGS_DIR / f"file_reads_{today}.log"


def log_file_read(*, path: str, success: bool, error: str = "") -> None:
    """记录一次文件读取操作。

    调用时机：每次 ``read_file_content`` 执行完毕后立即调用。

    Args:
        path: 实际读取的文件路径（解析后的绝对路径）。
        success: 读取是否成功。
        error: 失败时的错误描述，成功时为空字符串。
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "success": success,
        "error": error,
    }

    with _LOCK:
        _ensure_logs_dir()
        with open(_log_file_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_file_search(
    *,
    query: str,
    search_dir: str,
    match_count: int,
    files_scanned: int,
    files_skipped: int,
    errors: list[str],
) -> None:
    """记录一次文件搜索操作。

    调用时机：每次 ``search_files`` 执行完毕后立即调用。

    Args:
        query: 搜索关键词。
        search_dir: 搜索范围目录。
        match_count: 匹配到的结果数量。
        files_scanned: 已扫描的文件数。
        files_skipped: 跳过的文件数（无法读取等）。
        errors: 跳过文件时的错误原因列表。
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "search_dir": search_dir,
        "match_count": match_count,
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "errors": errors,
    }

    with _LOCK:
        _ensure_logs_dir()
        log_path = _LOGS_DIR / f"file_searches_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_email_audit(
    *,
    action: str,
    to_address: str,
    subject: str,
    confirmed: bool = False,
    whitelist_passed: bool = True,
    attachment_check_passed: bool = True,
    attachment_names: list[str] | None = None,
    error: str = "",
) -> None:
    """统一记录一次邮件操作的完整审计信息。

    所有邮件操作（发送、取消、拦截、失败）都通过此函数记录，
    字段统一，便于根据日志还原"一封邮件为什么被发送或拦截"。

    注意：**绝不会记录 SMTP 授权码。**

    Args:
        action: 操作结果，``"sent"`` | ``"cancelled"`` | ``"rejected"`` | ``"failed"``。
        to_address: 收件人邮箱地址。
        subject: 邮件主题。
        confirmed: 是否经过了用户确认。
        whitelist_passed: 是否通过了白名单检查。
        attachment_check_passed: 是否通过了附件安全检查。
        attachment_names: 附件文件名列表（无附件时省略）。
        error: 失败/拦截/取消的原因描述，成功时为空。
    """
    entry: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "to": to_address,
        "subject": subject,
        "confirmed": confirmed,
        "whitelist_passed": whitelist_passed,
        "attachment_check_passed": attachment_check_passed,
    }
    if attachment_names:
        entry["attachments"] = attachment_names
    if error:
        entry["error"] = error

    with _LOCK:
        _ensure_logs_dir()
        log_path = _LOGS_DIR / f"email_audit_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 以下为向后兼容的包装函数 ─────────────────────────────────


def log_email_send(
    *,
    to_address: str,
    subject: str,
    success: bool,
    error: str = "",
    attachment_count: int = 0,
    attachment_names: list[str] | None = None,
) -> None:
    """向后兼容：委托给 ``log_email_audit``。"""
    log_email_audit(
        action="sent" if success else "failed",
        to_address=to_address,
        subject=subject,
        confirmed=True,
        whitelist_passed=True,
        attachment_check_passed=True,
        attachment_names=attachment_names if attachment_count > 0 else None,
        error=error if not success else "",
    )


def log_email_cancelled(
    *,
    to_address: str,
    subject: str,
    reason: str = "用户取消发送",
) -> None:
    """向后兼容：委托给 ``log_email_audit``。"""
    log_email_audit(
        action="cancelled",
        to_address=to_address,
        subject=subject,
        confirmed=False,
        whitelist_passed=True,
        attachment_check_passed=True,
        error=reason,
    )


def log_email_rejected(
    *,
    to_address: str,
    subject: str,
    reason: str,
) -> None:
    """向后兼容：委托给 ``log_email_audit``。"""
    log_email_audit(
        action="rejected",
        to_address=to_address,
        subject=subject,
        confirmed=True,
        whitelist_passed="不在白名单中" not in reason,
        attachment_check_passed="附件" not in reason,
        error=reason,
    )
