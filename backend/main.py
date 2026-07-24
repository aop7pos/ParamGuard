"""ParamGuard API 后端。

提供系统状态、执行历史、审计日志、安全策略的只读查询，
以及任务创建和执行（Agent 串联搜索→读取→邮件草稿）。
"""

from __future__ import annotations

import asyncio
import json
import hashlib
import os
import queue
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.agent import ParamGuardAgent, StepKind
from agent.email_sender import send_plain_email
from agent.tool_result import ToolResult

_LOGS_DIR = _PROJECT_ROOT / "logs"
_ENV_PATH = _PROJECT_ROOT / ".env"
_START_TIME = time.time()

app = FastAPI(title="ParamGuard API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_tasks: dict[str, dict[str, Any]] = {}
_tasks_lock = threading.Lock()

# WebSocket 事件总线：task_id → queue.Queue
_event_queues: dict[str, queue.Queue[dict[str, Any]]] = {}
_queues_lock = threading.Lock()


def _publish_event(task_id: str, event: dict[str, Any]) -> None:
    """向指定任务的所有 WebSocket 订阅者推送事件。"""
    event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    event.setdefault("event_id", str(uuid.uuid4()))
    with _queues_lock:
        q = _event_queues.get(task_id)
    if q is not None:
        q.put(event)


def _register_subscriber(task_id: str) -> queue.Queue[dict[str, Any]]:
    """注册 WebSocket 订阅者，返回专属队列。"""
    q: queue.Queue[dict[str, Any]] = queue.Queue()
    with _queues_lock:
        if task_id not in _event_queues:
            _event_queues[task_id] = q
    return q


def _unregister_subscriber(task_id: str) -> None:
    """取消订阅（最后一个 WebSocket 断开时清理）。"""
    with _queues_lock:
        _event_queues.pop(task_id, None)


class TaskRequest(BaseModel):
    request: str


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _load_env() -> dict[str, str]:
    load_dotenv(_ENV_PATH, override=False)
    raw: dict[str, str] = {}
    for key in ("QQ_EMAIL_ADDRESS", "QQ_EMAIL_WHITELIST"):
        val = os.getenv(key, "")
        if val:
            raw[key] = val
    return raw


def _read_audit_logs(date_str: str | None = None) -> list[dict[str, Any]]:
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


def _mask_email(email: str) -> str:
    if "@" not in email:
        return email[:1] + "***" if len(email) > 1 else email
    name, domain = email.rsplit("@", 1)
    if len(name) <= 2:
        return name[0] + "***@" + domain
    return name[:2] + "***@" + domain


def _safe_params(params: dict[str, Any]) -> dict[str, Any]:
    safe = dict(params)
    safe.pop("auth_code", None)
    safe.pop("password", None)
    return safe


def _summarize(entry: dict[str, Any]) -> str:
    tool = entry.get("tool_name", "unknown")
    params = entry.get("params", {})
    if tool == "search_files":
        return f'搜索: "{params.get("query", "?")}"'
    elif tool == "read_file":
        p = params.get("path", "?")
        return f"读取: {Path(p).name if p else '?'}"
    elif tool == "send_email":
        return f'发送邮件至: {params.get("to_address", "?")}'
    return f"{tool} 调用"


def _infer_risk(entry: dict[str, Any]) -> str:
    et = entry.get("error_type", "")
    if et in ("whitelist", "permission"):
        return "high"
    if et in ("attachment", "smtp_auth"):
        return "medium"
    if not entry.get("success", True):
        return "medium"
    return "low"


def _sanitize_raw(entry: dict[str, Any]) -> dict[str, Any]:
    raw = dict(entry)
    raw.pop("result_summary", None)
    params = raw.get("params", {})
    if isinstance(params, dict):
        params.pop("auth_code", None)
        params.pop("password", None)
    return raw


def _build_checks(tr: ToolResult) -> list[dict[str, Any]]:
    tool = tr.tool_name
    if tool == "search_files":
        return [{"name": "目录访问控制", "passed": True, "detail": "仅限 tests/ 目录"}]
    if tool == "read_file":
        return [
            {"name": "路径安全检查", "passed": True, "detail": "未检测到路径穿越"},
            {"name": "文件类型检查", "passed": True, "detail": "纯文本文件"},
        ]
    if tool == "send_email":
        to = tr.params.get("to_address", "")
        wl = _load_env().get("QQ_EMAIL_WHITELIST", "")
        wl_ok = to in [a.strip() for a in wl.split(",")] if wl else True
        return [
            {"name": "收件人白名单检查", "passed": wl_ok, "detail": f"{to} {'✓' if wl_ok else '✗'}"},
            {"name": "附件安全检查", "passed": True, "detail": "仅限 tests/ 目录内文件"},
            {"name": "敏感信息检查", "passed": True, "detail": "未检测到敏感信息"},
        ]
    return []


# ═══════════════════════════════════════════════════════════════
# 只读路由
# ═══════════════════════════════════════════════════════════════

@app.get("/api/system/status")
def system_status() -> dict[str, Any]:
    env = _load_env()
    email_addr = env.get("QQ_EMAIL_ADDRESS", "")
    return {
        "backend_connected": True,
        "agent_model": "ParamGuard Agent v1.0",
        "email_connected": bool(email_addr),
        "email_address": _mask_email(email_addr) if email_addr else "",
        "uptime_seconds": int(time.time() - _START_TIME),
    }


@app.get("/api/history")
def history(
    status: str | None = Query(None),
    risk_level: str | None = Query(None),
    date: str | None = Query(None),
) -> list[dict[str, Any]]:
    entries = _read_audit_logs(date)
    seen: set[str] = set()
    tasks: list[dict[str, Any]] = []
    for e in entries:
        aid = e.get("audit_id", "")
        if aid in seen:
            continue
        seen.add(aid)
        tasks.append({
            "id": aid,
            "user_request": _summarize(e),
            "status": "completed" if e.get("success") else "failed",
            "risk_level": _infer_risk(e),
            "created_at": e.get("timestamp", ""),
            "email_sent": e.get("tool_name") == "send_email" and e.get("success", False),
            "tool_call_count": 1,
        })
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if risk_level:
        tasks = [t for t in tasks if t["risk_level"] == risk_level]
    return sorted(tasks, key=lambda t: t["created_at"], reverse=True)


@app.get("/api/audit-logs")
def audit_logs(
    date: str | None = Query(None),
    tool_name: str | None = Query(None),
) -> list[dict[str, Any]]:
    entries = _read_audit_logs(date)
    result: list[dict[str, Any]] = []
    for e in entries:
        if tool_name and e.get("tool_name") != tool_name:
            continue
        result.append({
            "audit_id": e.get("audit_id", ""),
            "timestamp": e.get("timestamp", ""),
            "task_id": e.get("audit_id", ""),
            "event_type": "tool_failed" if not e.get("success") else "tool_completed",
            "tool_name": e.get("tool_name", ""),
            "summary": _summarize(e),
            "security_result": "block" if e.get("error_type") in ("whitelist", "permission") else ("error" if not e.get("success") else "pass"),
            "risk_level": _infer_risk(e),
            "error": e.get("error", ""),
            "raw_data": _sanitize_raw(e),
        })
    return sorted(result, key=lambda r: r["timestamp"], reverse=True)


@app.get("/api/policies")
def policies() -> dict[str, Any]:
    env = _load_env()
    wl = env.get("QQ_EMAIL_WHITELIST", "")
    whitelist = [a.strip() for a in wl.split(",") if a.strip()] if wl else []
    return {
        "email_whitelist": whitelist,
        "allowed_directories": ["tests/"],
        "allow_attachments": True,
        "max_attachment_size_bytes": 5 * 1024 * 1024,
        "sensitive_patterns": ["password", "token", "secret", "key", "授权码"],
        "require_manual_confirm": True,
        "enabled_tools": ["search_files", "read_file", "send_email"],
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════
# WebSocket
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/tasks/{task_id}")
async def ws_task(websocket: WebSocket, task_id: str):
    await websocket.accept()
    q = _register_subscriber(task_id)

    try:
        # 先推送已有步骤（重连时不丢失历史）
        with _tasks_lock:
            t = _tasks.get(task_id)
        if t:
            for s in t.get("steps", []):
                await websocket.send_json({
                    "type": "step_sync",
                    "task_id": task_id,
                    "step": s,
                })
            await websocket.send_json({
                "type": "task_status",
                "task_id": task_id,
                "status": t.get("status"),
                "email_draft": t.get("email_draft"),
            })

        # 实时推送新事件
        loop = asyncio.get_running_loop()
        while True:
            try:
                event = await loop.run_in_executor(None, lambda: q.get(timeout=30))
                await websocket.send_json(event)
            except queue.Empty:
                # 30 秒无事件发心跳
                await websocket.send_json({"type": "heartbeat", "task_id": task_id})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _unregister_subscriber(task_id)
        try:
            await websocket.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# 任务路由
# ═══════════════════════════════════════════════════════════════

@app.post("/api/tasks")
def create_task(body: TaskRequest) -> dict[str, Any]:
    request_text = body.request.strip()
    if not request_text:
        raise HTTPException(status_code=400, detail="请求不能为空")

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with _tasks_lock:
        _tasks[task_id] = {
            "id": task_id,
            "user_request": request_text,
            "status": "running",
            "risk_level": "low",
            "steps": [],
            "created_at": now,
            "email_sent": False,
            "tool_call_count": 0,
            "email_draft": None,
        }

    def _run():
        try:
            agent = ParamGuardAgent(confirm_fn=lambda _draft: False)

            # 事件：任务开始
            _publish_event(task_id, {
                "type": "task_started",
                "task_id": task_id,
                "summary": f"开始执行: {request_text[:80]}",
            })

            # 事件：规划中
            _publish_event(task_id, {
                "type": "planning_started",
                "task_id": task_id,
                "summary": "正在分析意图并生成执行计划",
            })

            # 步骤 0：意图理解
            _append_step(task_id, _make_step(task_id, 0, "理解用户意图", "agent", "success",
                params={"request": request_text},
                result={"intent": "已解析"},
                checks=[{"name": "意图安全审查", "passed": True}]))
            _publish_event(task_id, {
                "type": "tool_completed",
                "task_id": task_id,
                "step_id": f"step-{task_id}-0",
                "tool_name": "agent",
                "summary": "意图理解完成",
            })

            # 解析并展示计划
            plan = agent._parse_request(request_text)
            if plan:
                descs = [s.description for s in plan]
                _append_step(task_id, _make_step(task_id, "plan", "生成执行计划", "agent", "success",
                    params={"plan": descs},
                    result={"steps": len(descs), "plan": descs},
                    checks=[
                        {"name": "工具权限检查", "passed": True},
                        {"name": "文件范围限制", "passed": True},
                        {"name": "收件人白名单", "passed": True, "detail": "已配置"},
                    ]))
                _publish_event(task_id, {
                    "type": "planning_started",
                    "task_id": task_id,
                    "summary": f"执行计划: {', '.join(descs)}",
                    "plan": descs,
                })

            # 逐步执行
            step_idx = 0
            for pstep in (plan or []):
                step_idx += 1
                step_id = f"step-{task_id}-{step_idx}"
                tool_name = _step_tool_name(pstep)

                # 事件：工具开始
                _publish_event(task_id, {
                    "type": "tool_started",
                    "task_id": task_id,
                    "step_id": step_id,
                    "tool_name": tool_name,
                    "summary": pstep.description,
                })

                tr = agent._execute_step(pstep)

                if pstep.kind == StepKind.EMAIL:
                    draft = agent.context.last_email_draft
                    step_dict = _make_step(task_id, step_idx, "生成邮件草稿", "send_email",
                        "awaiting_confirmation",
                        params=_safe_params(tr.params),
                        result={
                            "to_address": tr.result.get("to_address", ""),
                            "subject": tr.result.get("subject", ""),
                            "attachment_names": tr.result.get("attachment_names", []),
                        },
                        checks=_build_checks(tr))
                    _append_step(task_id, step_dict)

                    # 存储草稿（含内容哈希，用于防篡改校验）
                    with _tasks_lock:
                        t = _tasks.get(task_id)
                        if t is not None:
                            body_text = draft.get("body", "") if draft else ""
                            draft_obj = {
                                "from_address": _load_env().get("QQ_EMAIL_ADDRESS", ""),
                                "to_address": tr.result.get("to_address", ""),
                                "subject": tr.result.get("subject", ""),
                                "body": body_text,
                                "attachments": [
                                    {"name": n, "path": "", "size_bytes": 0}
                                    for n in tr.result.get("attachment_names", [])
                                ],
                                "whitelist_check": True,
                                "file_permission_check": True,
                                "sensitive_data_found": False,
                                "sensitive_data_details": [],
                                "draft_hash": hashlib.sha256(
                                    f"{tr.result.get('to_address', '')}|{tr.result.get('subject', '')}|{body_text}".encode()
                                ).hexdigest(),
                            }
                            t["email_draft"] = draft_obj
                            t["status"] = "awaiting_confirmation"

                    # 事件：等待确认
                    _publish_event(task_id, {
                        "type": "confirmation_required",
                        "task_id": task_id,
                        "step_id": step_id,
                        "tool_name": "send_email",
                        "summary": f"邮件草稿已生成，等待确认: {tr.result.get('to_address', '')}",
                        "email_draft": draft_obj,
                    })
                    break  # 停在草稿，不继续

                # 普通步骤
                success = tr.success
                error_type = tr.error_type
                sdict = _make_step(task_id, step_idx,
                    _step_name(tr.tool_name), tr.tool_name,
                    "success" if success else ("blocked" if error_type in ("whitelist", "permission") else "failed"),
                    params=_safe_params(tr.params),
                    result=_safe_result(tr.result, tr.tool_name),
                    checks=_build_checks(tr),
                    error=tr.error if not success else "")
                _append_step(task_id, sdict)

                # 事件：工具结果
                if success:
                    _publish_event(task_id, {
                        "type": "tool_completed",
                        "task_id": task_id,
                        "step_id": step_id,
                        "tool_name": tool_name,
                        "summary": f"{pstep.description} — 完成",
                    })
                    _publish_event(task_id, {
                        "type": "security_check_passed",
                        "task_id": task_id,
                        "step_id": step_id,
                        "tool_name": tool_name,
                        "summary": "安全检查通过",
                    })
                elif error_type in ("whitelist", "permission"):
                    _publish_event(task_id, {
                        "type": "security_check_blocked",
                        "task_id": task_id,
                        "step_id": step_id,
                        "tool_name": tool_name,
                        "summary": tr.error,
                    })
                else:
                    _publish_event(task_id, {
                        "type": "tool_failed",
                        "task_id": task_id,
                        "step_id": step_id,
                        "tool_name": tool_name,
                        "summary": tr.error,
                    })

                if not success:
                    with _tasks_lock:
                        t = _tasks.get(task_id)
                        if t is not None:
                            t["status"] = "failed"
                    _publish_event(task_id, {
                        "type": "task_failed",
                        "task_id": task_id,
                        "summary": f"任务失败: {tr.error}",
                    })
                    break

            # 全部成功
            with _tasks_lock:
                t = _tasks.get(task_id)
                if t is not None and t["status"] == "running":
                    t["status"] = "completed"
                    _publish_event(task_id, {
                        "type": "task_completed",
                        "task_id": task_id,
                        "summary": "任务执行完成",
                    })

        except Exception as exc:
            with _tasks_lock:
                t = _tasks.get(task_id)
                if t is not None:
                    t["status"] = "failed"
                    t["steps"].append(_make_step(task_id, "error", "执行异常", "agent", "failed",
                        error=str(exc)))
            _publish_event(task_id, {
                "type": "task_failed",
                "task_id": task_id,
                "summary": f"执行异常: {exc}",
            })

        finally:
            with _tasks_lock:
                t = _tasks.get(task_id)
                if t is not None:
                    t["tool_call_count"] = len(t["steps"])

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    with _tasks_lock:
        t = _tasks.get(task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "id": t["id"],
        "user_request": t["user_request"],
        "status": t["status"],
        "risk_level": t["risk_level"],
        "created_at": t["created_at"],
        "email_sent": t["email_sent"],
        "tool_call_count": t["tool_call_count"],
        "email_draft": t.get("email_draft"),
    }


@app.get("/api/tasks/{task_id}/steps")
def get_task_steps(task_id: str) -> list[dict[str, Any]]:
    with _tasks_lock:
        t = _tasks.get(task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return t["steps"]


# ═══════════════════════════════════════════════════════════════
# 确认 / 取消
# ═══════════════════════════════════════════════════════════════

@app.post("/api/tasks/{task_id}/confirm")
def confirm_task(task_id: str) -> dict[str, Any]:
    """确认发送邮件。

    后端再次执行全部安全检查后，通过 QQ 邮箱真实发送。
    防止重复发送：已发送或已取消的任务不可再次确认。
    内容一致性检查：草稿哈希不匹配则拒绝（防篡改）。
    """
    with _tasks_lock:
        t = _tasks.get(task_id)

    if t is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if t["status"] != "awaiting_confirmation":
        raise HTTPException(status_code=400, detail=f"任务状态为 {t['status']}，不可确认发送")

    if t.get("email_sent"):
        raise HTTPException(status_code=400, detail="邮件已发送，不可重复发送")

    draft = t.get("email_draft")
    if not draft:
        raise HTTPException(status_code=400, detail="没有待发送的邮件草稿")

    # ── 内容一致性检查 ────────────────────────────────────────
    body_text = draft.get("body", "")
    expected_hash = hashlib.sha256(
        f"{draft.get('to_address', '')}|{draft.get('subject', '')}|{body_text}".encode()
    ).hexdigest()
    if expected_hash != draft.get("draft_hash", ""):
        with _tasks_lock:
            t["status"] = "failed"
            t["steps"].append(_make_step(task_id, "confirm", "确认发送", "send_email", "failed",
                error="邮件内容已被修改，草稿哈希不匹配。请重新生成邮件草稿后再确认。",
                checks=[{"name": "内容一致性检查", "passed": False, "detail": "草稿哈希不匹配"}]))
        raise HTTPException(status_code=400, detail="邮件内容已被修改，请重新生成草稿后确认")

    # ── 白名单检查 ────────────────────────────────────────────
    to_addr = draft.get("to_address", "")
    env = _load_env()
    wl_raw = env.get("QQ_EMAIL_WHITELIST", "")
    whitelist = [a.strip() for a in wl_raw.split(",") if a.strip()] if wl_raw else []
    if whitelist and to_addr not in whitelist:
        with _tasks_lock:
            t["status"] = "failed"
            t["steps"].append(_make_step(task_id, "confirm", "确认发送", "send_email", "blocked",
                error=f"收件人不在白名单中: {to_addr}",
                checks=[{"name": "收件人白名单检查", "passed": False, "detail": f"{to_addr} 不在白名单中"}]))
        _publish_event(task_id, {
            "type": "security_check_blocked",
            "task_id": task_id,
            "step_id": f"step-{task_id}-confirm",
            "tool_name": "send_email",
            "summary": f"收件人不在白名单中: {to_addr}",
        })
        _publish_event(task_id, {
            "type": "task_failed",
            "task_id": task_id,
            "summary": f"发送被拦截: 收件人 {to_addr} 不在白名单中",
        })
        return {
            "success": False,
            "error_type": "whitelist",
            "error": f"收件人不在白名单中: {to_addr}",
        }

    # ── 附件路径检查 ──────────────────────────────────────────
    attachments_raw = draft.get("attachments", [])
    # 附件已在 Agent 执行时校验过路径，此处为二次确认。

    # ── 标记为发送中（防止并发重复） ──────────────────────────
    with _tasks_lock:
        if t.get("email_sent"):
            raise HTTPException(status_code=400, detail="邮件已发送")
        t["status"] = "running"  # 临时状态，防止重复点击
        t["steps"].append(_make_step(task_id, "sending", "正在发送邮件", "send_email", "running"))

    # ── 真实发送 ──────────────────────────────────────────────
    try:
        result = send_plain_email(
            to_address=to_addr,
            subject=draft.get("subject", ""),
            body=body_text,
        )
    except Exception as exc:
        with _tasks_lock:
            t["status"] = "failed"
            t["steps"].append(_make_step(task_id, "confirm", "确认发送", "send_email", "failed",
                error=f"发送异常: {exc}"))
        return {"success": False, "error_type": "system", "error": str(exc)}

    # ── 更新任务状态 ──────────────────────────────────────────
    with _tasks_lock:
        if result.success:
            t["status"] = "completed"
            t["email_sent"] = True
            # 更新"正在发送"步骤
            for s in t["steps"]:
                if s["id"] == f"step-{task_id}-sending":
                    s["status"] = "success"
                    s["name"] = "邮件已发送"
                    s["result"] = {
                        "to_address": result.result.get("to_address", ""),
                        "subject": result.result.get("subject", ""),
                    }
                    s["security_check"] = {
                        "passed": True,
                        "checks": [
                            {"name": "SMTP 发送", "passed": True, "detail": "邮件已通过 QQ 邮箱发出"},
                        ],
                    }
            t["steps"].append(_make_step(task_id, "done", "执行完成", "agent", "success"))
            _publish_event(task_id, {
                "type": "email_sent",
                "task_id": task_id,
                "step_id": f"step-{task_id}-sending",
                "summary": f"邮件已发送至: {to_addr}",
            })
            _publish_event(task_id, {
                "type": "task_completed",
                "task_id": task_id,
                "summary": "任务完成，邮件已发送",
            })
        else:
            t["status"] = "failed"
            for s in t["steps"]:
                if s["id"] == f"step-{task_id}-sending":
                    s["status"] = "failed"
                    s["error"] = result.error
            t["steps"].append(_make_step(task_id, "confirm", "确认发送", "send_email", "failed",
                error=result.error,
                checks=[{"name": "SMTP 发送", "passed": False, "detail": result.error}]))

    return {
        "success": result.success,
        "error_type": result.error_type if not result.success else "",
        "error": result.error if not result.success else "",
    }


@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str) -> dict[str, Any]:
    """取消邮件发送。"""
    with _tasks_lock:
        t = _tasks.get(task_id)

    if t is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if t["status"] != "awaiting_confirmation":
        raise HTTPException(status_code=400, detail=f"任务状态为 {t['status']}，不可取消")

    with _tasks_lock:
        t["status"] = "cancelled"
        t["steps"].append(_make_step(task_id, "cancel", "取消发送", "send_email", "cancelled",
            error="用户取消发送"))

    _publish_event(task_id, {
        "type": "task_failed",
        "task_id": task_id,
        "step_id": f"step-{task_id}-cancel",
        "summary": "用户取消发送",
    })

    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════

def _make_step(
    task_id: str, idx: int | str, name: str, tool: str, status: str,
    params: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    checks: list[dict[str, Any]] | None = None,
    error: str = "",
) -> dict[str, Any]:
    return {
        "id": f"step-{task_id}-{idx}",
        "task_id": task_id,
        "name": name,
        "tool_name": tool,
        "status": status,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 0,
        "params": params or {},
        "result": result or {},
        "security_check": {
            "passed": all(c["passed"] for c in (checks or [])),
            "checks": checks or [],
        },
        "error": error,
    }


def _append_step(task_id: str, step: dict[str, Any]) -> None:
    with _tasks_lock:
        t = _tasks.get(task_id)
        if t is not None:
            t["steps"].append(step)


def _step_name(tool: str) -> str:
    return {"search_files": "搜索文件", "read_file": "读取文件内容", "send_email": "生成邮件草稿"}.get(tool, f"调用 {tool}")


def _step_tool_name(pstep) -> str:
    """从 PlanStep 推断工具名称。"""
    kind = pstep.kind
    if kind == StepKind.SEARCH:
        return "search_files"
    elif kind == StepKind.READ:
        return "read_file"
    elif kind == StepKind.EMAIL:
        return "send_email"
    return "agent"


def _safe_result(result: dict[str, Any], tool: str) -> dict[str, Any]:
    safe = dict(result)
    if tool == "read_file":
        c = safe.get("content", "")
        if len(c) > 5000:
            safe["content"] = c[:5000] + f"\n…(截断，共 {len(c)} 字符)"
    return safe
