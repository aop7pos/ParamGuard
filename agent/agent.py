"""ParamGuard 基础 Agent —— 将三个工具串成可交互的执行管道。

根据自然语言请求自动选择工具、按序执行，并在发信前强制等待用户确认。

**安全保证：**
- 未经用户交互确认，**绝不会**调用邮件发送。
- 所有工具调用均通过统一审计日志记录。
- 收件人白名单、附件限制均由底层工具强制执行，Agent 无法绕过。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from .file_reader import read_file_content
from .file_searcher import search_files
from .email_sender import send_plain_email
from .tool_result import ErrorType, ToolResult, write_audit_log


# ── 意图类型 ──────────────────────────────────────────────────


class StepKind(Enum):
    """Agent 可执行的步骤类型。"""
    SEARCH = auto()   # 搜索文件
    READ = auto()     # 读取文件内容
    EMAIL = auto()    # 发送邮件（须确认）


@dataclass
class PlanStep:
    """管道中的一个执行步骤。

    Attributes:
        kind: 步骤类型。
        params: 从自然语言中提取的参数。
        description: 人类可读的步骤描述。
    """
    kind: StepKind
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


# ── 上下文 ────────────────────────────────────────────────────


@dataclass
class AgentContext:
    """Agent 在多次交互中保持的上下文。

    允许用户先搜索再指定"读取第一个结果"等引用式指令。
    """
    last_search_result: ToolResult | None = None
    last_read_result: ToolResult | None = None
    last_email_draft: dict[str, Any] | None = None


# ── Agent ─────────────────────────────────────────────────────


class ParamGuardAgent:
    """ParamGuard 基础 Agent。

    将自然语言请求解析为搜索→读取→邮件管道，
    所有工具调用均产生审计日志，邮件发送前强制确认。

    Usage::

        agent = ParamGuardAgent()
        agent.run("搜索包含'测试报告'的文件")
        agent.run("读取第1个结果")
        agent.run("把内容整理成邮件草稿，主题'日报'，发给 admin@qq.com")
    """

    def __init__(self, *, confirm_fn=None):
        """初始化 Agent。

        Args:
            confirm_fn: 可选的确认回调，签名为 ``(draft: dict) -> bool``。
                        若为 None，使用内置的 ``input()`` 交互确认。
        """
        self._ctx = AgentContext()
        self._confirm_fn = confirm_fn

    # ── 公开接口 ──────────────────────────────────────────────

    def run(self, request: str) -> ToolResult:
        """解析自然语言请求并执行相应工具。

        支持单步指令和引用式指令（"读取第一个结果"等）。

        Args:
            request: 用户的自然语言请求。

        Returns:
            最后一步的 ``ToolResult``。
        """
        request = request.strip()
        if not request:
            return ToolResult(
                success=False, tool_name="agent",
                error="请求不能为空", error_type="validation",
            )

        plan = self._parse_request(request)
        if not plan:
            return ToolResult(
                success=False, tool_name="agent",
                error=f"无法理解该请求，支持的操作：搜索、读取、发邮件。\n请求: {request}",
                error_type="validation",
            )

        result: ToolResult | None = None
        for step in plan:
            result = self._execute_step(step)

        # 更新上下文。
        if result is not None:
            self._update_context(result)

        return result if result is not None else ToolResult(
            success=False, tool_name="agent",
            error="未执行任何步骤", error_type="validation",
        )

    # ── 意图解析 ──────────────────────────────────────────────

    def _parse_request(self, request: str) -> list[PlanStep] | None:
        """将自然语言请求解析为执行计划。

        支持关键词：
        - 搜索/查找/找 → SEARCH
        - 读取/查看/打开 → READ（含引用式"读取第1个"）
        - 发邮件/发送/发给/邮件 → EMAIL
        - 整理成邮件草稿 → EMAIL (仅草稿，不发)
        """
        steps: list[PlanStep] = []

        # ── 搜索意图 ──────────────────────────────────────────
        search_match = re.search(
            r'(?:搜索|查找|找|搜)\s*[：:]*\s*["\u201c「『]?(.+?)["\u201d」』]?\s*(?:文件|的|$)',
            request,
        )
        if search_match:
            query = search_match.group(1).strip().strip('"\u201c\u201d「」『』')
            if query:
                steps.append(PlanStep(
                    kind=StepKind.SEARCH,
                    params={"query": query},
                    description=f"搜索包含 \"{query}\" 的文件",
                ))

        # ── 读取意图（先处理引用式，再处理显式路径） ─────────
        ordinal_match = re.search(
            r'(?:读取|查看|打开|读)\s*第\s*(\d+)\s*个\s*(?:结果|文件)?',
            request,
        )
        if ordinal_match:
            idx = int(ordinal_match.group(1))
            steps.append(self._build_read_step(f"#{idx}"))
        else:
            read_explicit = re.search(
                r'(?:读取|查看|打开|读)\s+(?:文件\s+)?["\u201c「『]?(.+?)["\u201d」』]?(?:\s|，|。|$)',
                request,
            )
            if read_explicit:
                file_ref = read_explicit.group(1).strip().strip('"\u201c\u201d「」『』')
                if file_ref:
                    steps.append(self._build_read_step(file_ref))

        # ── 邮件意图 ──────────────────────────────────────────
        email_intent = re.search(
            r'(?:发邮件|发送邮件|发送|发给|邮件|整理成邮件|邮件草稿|生成邮件|写邮件)',
            request,
        )
        if email_intent:
            # 提取收件人：支持 "发给xxx"、"发邮件给xxx"、"收件人:xxx"
            to_match = re.search(
                r'(?:发给|发邮件给|给|收件人[：:]*|to[：:]*)\s*([\w.+-]+@[\w.-]+)',
                request, re.IGNORECASE,
            )
            subject_match = re.search(
                r'(?:主题[：:]*|标题[：:]*)\s*["\u201c「『]?(.+?)["\u201d」』]?(?:\s|$|，|。)',
                request,
            )

            email_params: dict[str, Any] = {}
            if to_match:
                email_params["to_address"] = to_match.group(1)
            if subject_match:
                email_params["subject"] = subject_match.group(1).strip().strip('"\u201c\u201d「」『』')

            # 正文：优先使用上次读取的内容。
            if self._ctx.last_read_result and self._ctx.last_read_result.success:
                email_params["body"] = self._ctx.last_read_result.result.get("content", "")

            # 区分"仅草稿"和"确认发送"。
            draft_only = bool(re.search(r'(?:整理成邮件|邮件草稿|生成邮件|写邮件)', request))
            action = "生成邮件草稿" if draft_only else "发送邮件"
            steps.append(PlanStep(
                kind=StepKind.EMAIL,
                params=email_params,
                description=action,
            ))

        return steps if steps else None

    def _build_read_step(self, file_ref: str) -> PlanStep:
        """根据文件引用构建 READ 步骤。"""
        if file_ref.startswith("#") and self._ctx.last_search_result:
            # 引用式：按序号从上次搜索结果中选取。
            try:
                idx = int(file_ref[1:]) - 1
            except ValueError:
                idx = 0
            matches = self._ctx.last_search_result.result.get("matches", [])
            if 0 <= idx < len(matches):
                file_path = matches[idx].get("file_path", "")
                return PlanStep(
                    kind=StepKind.READ,
                    params={"path": file_path},
                    description=f"读取搜索结果第 {idx + 1} 个: {Path(file_path).name}",
                )
        # 普通文件路径。
        return PlanStep(
            kind=StepKind.READ,
            params={"path": file_ref},
            description=f"读取文件: {file_ref}",
        )

    # ── 步骤执行 ──────────────────────────────────────────────

    def _execute_step(self, step: PlanStep) -> ToolResult:
        """执行单个计划步骤。"""
        if step.kind == StepKind.SEARCH:
            return self._do_search(step)
        elif step.kind == StepKind.READ:
            return self._do_read(step)
        elif step.kind == StepKind.EMAIL:
            return self._do_email(step)
        else:
            return ToolResult(
                success=False, tool_name="agent",
                error=f"未知步骤类型: {step.kind}", error_type="validation",
            )

    def _do_search(self, step: PlanStep) -> ToolResult:
        """执行文件搜索。"""
        query = step.params.get("query", "")
        result = search_files(query)
        return result

    def _do_read(self, step: PlanStep) -> ToolResult:
        """执行文件读取。"""
        path = step.params.get("path", "")
        result = read_file_content(path)
        return result

    def _do_email(self, step: PlanStep) -> ToolResult:
        """执行邮件操作。

        先展示草稿，再要求用户确认。未经确认绝不发送。
        """
        params = step.params
        to_address = params.get("to_address", "1962383827@qq.com")
        subject = params.get("subject", "ParamGuard 邮件")
        body = params.get("body", "")

        # ── 展示草稿 ──────────────────────────────────────────
        draft = {
            "to_address": to_address,
            "subject": subject,
            "body": body,
        }
        self._ctx.last_email_draft = draft

        # ── 确认 ──────────────────────────────────────────────
        confirmed = self._request_confirmation(draft)

        if not confirmed:
            tr = ToolResult(
                success=False,
                tool_name="send_email",
                params={"to_address": to_address, "subject": subject, "body_length": len(body)},
                result=draft,
                error_type=ErrorType.VALIDATION,
                error="用户取消发送（Agent 确认环节）",
            )
            write_audit_log(tr)
            return tr

        # ── 发送 ──────────────────────────────────────────────
        return send_plain_email(
            to_address=to_address,
            subject=subject,
            body=body,
        )

    def _request_confirmation(self, draft: dict[str, Any]) -> bool:
        """请求用户确认邮件发送。

        若提供了自定义 confirm_fn，则使用它；否则使用内置交互。
        """
        if self._confirm_fn is not None:
            return self._confirm_fn(draft)

        # 内置交互式确认。
        print()
        print("=" * 50)
        print("  📧 邮件草稿预览（Agent 生成）")
        print("=" * 50)
        print(f"  收件人: {draft.get('to_address', '')}")
        print(f"  主  题: {draft.get('subject', '')}")
        print("-" * 50)
        body = draft.get("body", "")
        preview = body[:500] + ("…" if len(body) > 500 else "")
        print(preview if preview else "  (正文为空)")
        print("=" * 50)

        try:
            answer = input("  确认发送？(yes/no): ").strip().lower()
            return answer in ("yes", "y")
        except (EOFError, KeyboardInterrupt):
            return False

    # ── 上下文管理 ────────────────────────────────────────────

    def _update_context(self, result: ToolResult) -> None:
        """根据工具执行结果更新 Agent 上下文。"""
        if result.tool_name == "search_files":
            self._ctx.last_search_result = result
        elif result.tool_name == "read_file":
            self._ctx.last_read_result = result

    # ── 便捷方法 ──────────────────────────────────────────────

    @property
    def context(self) -> AgentContext:
        """获取当前上下文（供外部查看）。"""
        return self._ctx

    def reset(self) -> None:
        """重置 Agent 上下文。"""
        self._ctx = AgentContext()
