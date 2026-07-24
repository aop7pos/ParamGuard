"""ParamGuard 只读 API 后端。

为前端提供系统状态、执行历史、审计日志和安全策略的只读查询。
所有数据来源均为项目现有文件（日志、配置），不修改 Agent 核心逻辑。
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# 项目根目录。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"
_ENV_PATH = _PROJECT_ROOT / ".env"

# 服务器启动时间。
_START_TIME = time.time()

app = FastAPI(title="ParamGuard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── 工具函数 ──────────────────────────────────────────────────

def _load_env() -> dict[str, str]:
    """安全加载 .env，返回脱敏后的键值对。"""
    load_dotenv(_ENV_PATH, override=False)
    raw: dict[str, str] = {}
    for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_WHITELIST"):
        val = os.getenv(key, "")
        if val:
            raw[key] = val
    # 绝不返回 QQ_EMAIL_AUTH_CODE。
    return raw


def _read_audit_logs(date_str: str | None = None) -> list[dict[str, Any]]:
    """读取指定日期的统一审计日志。"""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = _LOGS_DIR / f"tool_audit_{date_str}.log"
    if not log_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


# ── 路由：系统状态 ────────────────────────────────────────────


@app.get("/api/system/status")
def system_status() -> dict[str, Any]:
    """返回后端系统状态（不含授权码）。"""
    env = _load_env()
    up = int(time.time() - _START_TIME)
    email_addr = env.get("QQ_EMAIL_ADDRESS", "")
    return {
        "backend_connected": True,
        "agent_model": "ParamGuard Agent v1.0",
        "email_connected": bool(email_addr),
        "email_address": _mask_email(email_addr) if email_addr else "",
        "uptime_seconds": up,
    }


def _mask_email(email: str) -> str:
    """脱敏邮箱地址，如 ``ab***@qq.com``。"""
    if "@" not in email:
        return email[:1] + "***" if len(email) > 1 else email
    name, domain = email.rsplit("@", 1)
    if len(name) <= 2:
        return name[0] + "***@" + domain
    return name[:2] + "***@" + domain


# ── 路由：执行历史 ───────────────────────────────────────────


@app.get("/api/history")
def history(
    status: str | None = Query(None),
    risk_level: str | None = Query(None),
    date: str | None = Query(None),
) -> list[dict[str, Any]]:
    """返回执行历史（从审计日志聚合）。

    可选筛选：status、risk_level、date (YYYY-MM-DD)。
    """
    entries = _read_audit_logs(date)

    # 按 audit_id 去重聚合为任务视图。
    tasks: list[dict[str, Any]] = []
    for e in entries:
        tasks.append({
            "id": e.get("audit_id", ""),
            "user_request": _summarize(e),
            "status": "completed" if e.get("success") else "failed",
            "risk_level": _infer_risk(e),
            "created_at": e.get("timestamp", ""),
            "email_sent": e.get("tool_name") == "send_email" and e.get("success", False),
            "tool_call_count": 1,
        })

    # 筛选。
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if risk_level:
        tasks = [t for t in tasks if t["risk_level"] == risk_level]

    return sorted(tasks, key=lambda t: t["created_at"], reverse=True)


def _summarize(entry: dict[str, Any]) -> str:
    """从审计条目生成人类可读摘要。"""
    tool = entry.get("tool_name", "unknown")
    params = entry.get("params", {})
    if tool == "search_files":
        return f'搜索: "{params.get("query", "?")}"'
    elif tool == "read_file":
        p = params.get("path", "?")
        return f"读取: {Path(p).name if p else '?'}"
    elif tool == "send_email":
        return f'发送邮件至: {params.get("to_address", "?")}'
    elif tool == "agent":
        return "Agent 任务"
    return f"{tool} 调用"


def _infer_risk(entry: dict[str, Any]) -> str:
    """从审计条目推断风险等级。"""
    error_type = entry.get("error_type", "")
    if error_type in ("whitelist", "permission"):
        return "high"
    if error_type in ("attachment", "smtp_auth"):
        return "medium"
    if not entry.get("success", True):
        return "medium"
    return "low"


# ── 路由：审计日志 ───────────────────────────────────────────


@app.get("/api/audit-logs")
def audit_logs(
    date: str | None = Query(None),
    tool_name: str | None = Query(None),
) -> list[dict[str, Any]]:
    """返回审计日志（直接来自 tool_audit 日志文件）。

    可选筛选：date (YYYY-MM-DD)、tool_name。
    """
    entries = _read_audit_logs(date)

    result: list[dict[str, Any]] = []
    for e in entries:
        if tool_name and e.get("tool_name") != tool_name:
            continue
        result.append({
            "audit_id": e.get("audit_id", ""),
            "timestamp": e.get("timestamp", ""),
            "task_id": e.get("audit_id", ""),  # 当前用 audit_id 作为 task_id
            "event_type": _event_type(e),
            "tool_name": e.get("tool_name", ""),
            "summary": _summarize(e),
            "security_result": "block" if e.get("error_type") in ("whitelist", "permission") else ("error" if not e.get("success") else "pass"),
            "risk_level": _infer_risk(e),
            "error": e.get("error", ""),
            "raw_data": _sanitize_raw(e),
        })

    return sorted(result, key=lambda r: r["timestamp"], reverse=True)


def _event_type(entry: dict[str, Any]) -> str:
    """推断事件类型。"""
    if not entry.get("success"):
        return "tool_failed"
    if entry.get("error_type") == "whitelist":
        return "security_check_blocked"
    return "tool_completed"


def _sanitize_raw(entry: dict[str, Any]) -> dict[str, Any]:
    """生成脱敏后的 raw_data。"""
    raw = dict(entry)
    # 移除 result_summary 中的敏感路径信息。
    raw.pop("result_summary", None)
    # 确保 params 中没有 auth_code。
    params = raw.get("params", {})
    if isinstance(params, dict):
        params.pop("auth_code", None)
        params.pop("password", None)
    return raw


# ── 路由：安全策略 ───────────────────────────────────────────


@app.get("/api/policies")
def policies() -> dict[str, Any]:
    """返回当前安全策略（只读）。"""
    env = _load_env()
    whitelist_raw = env.get("QQ_EMAIL_WHITELIST", "")
    whitelist = [a.strip() for a in whitelist_raw.split(",") if a.strip()] if whitelist_raw else []

    return {
        "email_whitelist": whitelist,
        "allowed_directories": ["tests/"],
        "allow_attachments": True,
        "max_attachment_size_bytes": 5 * 1024 * 1024,
        "sensitive_patterns": ["password", "token", "secret", "key", "授权码"],
        "require_manual_confirm": True,
        "enabled_tools": ["search_files", "read_file", "send_email"],
    }


# ── 健康检查 ──────────────────────────────────────────────────


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
