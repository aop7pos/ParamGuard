"""ParamGuard Agent 交互式命令行入口。

用法::

    python tools/agent_cli.py

进入交互模式后，输入自然语言指令即可驱动 Agent 搜索、读取、发邮件。
输入 ``/help`` 查看帮助，``/quit`` 退出。
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

# 确保直接运行脚本时也能找到项目内的 agent 包。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.agent import ParamGuardAgent


# ── 帮助信息 ──────────────────────────────────────────────────

_HELP_TEXT = """
══════════════════════════════════════════════════════════════
  ParamGuard Agent — 将搜索、读取、邮件串联执行
══════════════════════════════════════════════════════════════

支持的自然语言指令示例：

  🔍 搜索：
     搜索包含"测试报告"的文件
     查找"日志"
     找 .txt 文件

  📖 读取：
     读取 tests/demo.txt
     查看第1个结果          （需先搜索）
     打开最后一个文件       （需先搜索）

  ✉️  邮件：
     把内容整理成邮件草稿，主题"日报"，发给 admin@qq.com
     发邮件给 user@qq.com，主题"通知"

  🔗 管道（一句话串联）：
     搜索"报告"然后发给 admin@qq.com

  每次发送前都会展示草稿并要求确认，**未经确认绝不发信**。

命令：
  /help      显示本帮助
  /reset     重置上下文（清除搜索/读取缓存）
  /context   查看当前上下文
  /quit      退出
══════════════════════════════════════════════════════════════
"""


# ── 主循环 ────────────────────────────────────────────────────


def _print_result(result) -> None:
    """格式化输出 ToolResult。"""
    if result.tool_name == "search_files":
        res = result.result
        matches = res.get("matches", [])
        if result.success:
            print(f"\n  找到 {res.get('match_count', 0)} 个匹配（扫描 {res.get('files_scanned', 0)} 个文件）:")
            for i, m in enumerate(matches, 1):
                tag = "[文件名]" if m.get("match_type") == "filename" else "[内容]"
                print(f"  {i}. {tag} {m.get('file_name', '?')}")
                print(f"     {m.get('file_path', '')}")
                snippet = m.get("snippet", "")
                if snippet and m.get("match_type") == "content":
                    print(f"     …{snippet[:80]}…")
            if res.get("files_skipped", 0) > 0:
                print(f"  ⚠ 跳过 {res.get('files_skipped')} 个无法读取的文件")
        else:
            print(f"\n  ❌ 搜索失败: {result.error}")

    elif result.tool_name == "read_file":
        if result.success:
            content = result.result.get("content", "")
            path = result.result.get("path", "")
            print(f"\n  ✅ 已读取: {Path(path).name}")
            print(f"  ──────────────────────────────────────────")
            preview = content[:1000]
            print(textwrap.indent(preview, "  "))
            if len(content) > 1000:
                print(f"  …(共 {len(content)} 字符，仅展示前 1000)")
            print(f"  ──────────────────────────────────────────")
        else:
            print(f"\n  ❌ 读取失败: {result.error}")

    elif result.tool_name == "send_email":
        if result.success:
            to_addr = result.result.get("to_address", "")
            print(f"\n  ✅ 邮件已发送至: {to_addr}")
            atts = result.result.get("attachment_names", [])
            if atts:
                print(f"  📎 附件: {', '.join(atts)}")
        else:
            if "取消" in result.error:
                print(f"\n  ⚠ 已取消发送。")
            else:
                print(f"\n  ❌ 发送失败 [{result.error_type}]: {result.error}")

    else:
        if not result.success:
            print(f"\n  ❌ {result.error}")
        else:
            print(f"\n  ✅ 完成")


def _print_context(agent: ParamGuardAgent) -> None:
    """打印当前 Agent 上下文。"""
    ctx = agent.context
    print("\n  ── 当前上下文 ──")
    if ctx.last_search_result:
        mc = ctx.last_search_result.result.get("match_count", 0)
        print(f"  上次搜索: {mc} 个结果")
    else:
        print(f"  上次搜索: (无)")
    if ctx.last_read_result:
        path = ctx.last_read_result.result.get("path", "")
        print(f"  上次读取: {Path(path).name if path else '(无)'}")
    else:
        print(f"  上次读取: (无)")
    if ctx.last_email_draft:
        print(f"  邮件草稿: 收件人={ctx.last_email_draft.get('to_address', '')}, "
              f"主题={ctx.last_email_draft.get('subject', '')}")
    else:
        print(f"  邮件草稿: (无)")
    print()


def main() -> int:
    """交互式 Agent 主循环。"""
    agent = ParamGuardAgent()

    print(_HELP_TEXT)

    while True:
        try:
            request = input("\n🔹 ParamGuard > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  已退出。")
            return 0

        if not request:
            continue

        # ── 命令处理 ──────────────────────────────────────────
        if request.startswith("/"):
            cmd = request.lower()
            if cmd in ("/quit", "/exit", "/q"):
                print("  已退出。")
                return 0
            elif cmd in ("/help", "/h", "/?"):
                print(_HELP_TEXT)
            elif cmd == "/reset":
                agent.reset()
                print("  上下文已重置。")
            elif cmd == "/context":
                _print_context(agent)
            else:
                print(f"  未知命令: {request}\n  输入 /help 查看帮助。")
            continue

        # ── 执行请求 ──────────────────────────────────────────
        result = agent.run(request)
        _print_result(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
