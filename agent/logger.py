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


def log_email_send(
    *,
    to_address: str,
    subject: str,
    success: bool,
    error: str = "",
) -> None:
    """记录一次邮件发送操作。

    调用时机：每次 ``send_plain_email`` 执行完毕后立即调用。
    注意：不会记录授权码等敏感信息。

    Args:
        to_address: 收件人邮箱地址。
        subject: 邮件主题。
        success: 是否发送成功。
        error: 失败时的错误描述，成功时为空字符串。
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "to": to_address,
        "subject": subject,
        "success": success,
        "error": error,
    }

    with _LOCK:
        _ensure_logs_dir()
        log_path = _LOGS_DIR / f"email_sends_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_email_cancelled(
    *,
    to_address: str,
    subject: str,
    reason: str = "用户取消发送",
) -> None:
    """记录一次邮件发送被取消的操作。

    调用时机：用户在确认环节选择取消时立即调用。

    Args:
        to_address: 收件人邮箱地址。
        subject: 邮件主题。
        reason: 取消原因，默认为用户主动取消。
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "cancelled",
        "to": to_address,
        "subject": subject,
        "reason": reason,
    }

    with _LOCK:
        _ensure_logs_dir()
        log_path = _LOGS_DIR / f"email_sends_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
