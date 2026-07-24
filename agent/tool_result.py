"""统一工具执行结果与审计日志模块。

所有工具（read_file、search_files、send_email）均返回 ``ToolResult``，
Agent 无需分别适配三种不同的返回结构。

审计日志统一写入 ``logs/tool_audit_{date}.log``，**绝不包含敏感信息**
（如邮箱授权码、密码等）。
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 项目根目录与日志目录。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"
_LOCK = threading.Lock()


# ── 统一返回结构 ──────────────────────────────────────────────


@dataclass
class ToolResult:
    """所有工具的统一执行结果。

    Attributes:
        success: 是否执行成功。
        tool_name: 工具名称，如 ``"read_file"``、``"search_files"``、``"send_email"``。
        params: 调用时传入的参数（已脱敏，不含授权码/密码）。
        result: 工具专属的执行结果数据。
        error_type: 错误分类，成功时为空字符串。
            可选值：``"validation"`` | ``"permission"`` | ``"system"`` |
            ``"whitelist"`` | ``"config"`` | ``"smtp_auth"`` | ``"smtp"`` |
            ``"network"`` | ``"attachment"``。
        error: 人类可读的错误描述，成功时为空字符串。
        timestamp: 操作时间（ISO 8601 格式，UTC 时区）。
        audit_id: 审计记录唯一编号（UUID v4）。
    """
    success: bool
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error_type: str = ""
    error: str = ""
    timestamp: str = ""
    audit_id: str = ""

    def __post_init__(self) -> None:
        """自动填充时间戳和审计编号。"""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.audit_id:
            self.audit_id = str(uuid.uuid4())


# ── 错误类型常量 ──────────────────────────────────────────────

class ErrorType:
    """统一的错误类型枚举。"""
    VALIDATION = "validation"        # 输入参数校验失败
    PERMISSION = "permission"        # 路径越权（试图访问授权目录之外）
    SYSTEM = "system"                # 操作系统/文件系统错误
    WHITELIST = "whitelist"          # 收件人不在白名单中
    CONFIG = "config"                # 配置缺失（如 .env 未配置）
    SMTP_AUTH = "smtp_auth"         # SMTP 认证失败
    SMTP = "smtp"                   # SMTP 通用错误
    NETWORK = "network"             # 网络连接失败
    ATTACHMENT = "attachment"       # 附件校验失败


# ── 统一审计日志 ──────────────────────────────────────────────


def _ensure_logs_dir() -> None:
    """确保日志目录存在。"""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _audit_log_path() -> Path:
    """返回当天的统一审计日志文件路径。"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _LOGS_DIR / f"tool_audit_{today}.log"


def write_audit_log(tool_result: ToolResult) -> None:
    """将 ToolResult 写入统一审计日志。

    **绝不记录 SMTP 授权码、密码等敏感信息。**
    调用方在构造 ``ToolResult.params`` 时已负责脱敏。

    Args:
        tool_result: 工具执行结果。
    """
    # 构造日志条目，确保不包含任何敏感字段。
    entry: dict[str, Any] = {
        "audit_id": tool_result.audit_id,
        "timestamp": tool_result.timestamp,
        "tool_name": tool_result.tool_name,
        "success": tool_result.success,
        "params": tool_result.params,
        "result_summary": _summarize_result(tool_result),
        "error_type": tool_result.error_type,
        "error": tool_result.error,
    }

    with _LOCK:
        _ensure_logs_dir()
        with open(_audit_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _summarize_result(tool_result: ToolResult) -> dict[str, Any]:
    """生成结果摘要，避免日志中写入完整文件内容等大字段。

    对于可能包含敏感或大量数据的字段进行截断或摘要处理。
    """
    summary: dict[str, Any] = {}
    result = tool_result.result

    if tool_result.tool_name == "read_file":
        summary["path"] = result.get("path", "")
        content = result.get("content", "")
        summary["content_length"] = len(content)
        summary["content_preview"] = content[:200] if content else ""

    elif tool_result.tool_name == "search_files":
        summary["query"] = result.get("query", "")
        summary["match_count"] = result.get("match_count", 0)
        summary["files_scanned"] = result.get("files_scanned", 0)
        summary["files_skipped"] = result.get("files_skipped", 0)

    elif tool_result.tool_name == "send_email":
        summary["to_address"] = result.get("to_address", "")
        summary["subject"] = result.get("subject", "")
        summary["attachment_count"] = len(result.get("attachment_names", []))
        # 绝不记录正文内容（可能含敏感信息）。

    return summary
