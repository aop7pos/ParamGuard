"""发送测试邮件的命令行工具。

**必须手动确认后才会真正发送。**
未确认时仅展示预览，取消后记录日志，绝不会发信。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.email_sender import send_plain_email


def _print_preview(
    to_address: str,
    subject: str,
    body: str,
    attachments: list[str] | None = None,
) -> None:
    """展示待发送邮件的预览，包含附件信息。"""
    print("=" * 50)
    print("  📧 待发送邮件预览")
    print("=" * 50)
    print(f"  收件人: {to_address}")
    print(f"  主  题: {subject}")
    if attachments:
        print(f"  附  件: {len(attachments)} 个")
        for att in attachments:
            print(f"    - {att}")
    print("-" * 50)
    print(body)
    print("=" * 50)


def _prompt_confirm() -> bool:
    """询问用户是否确认发送，返回 True 表示确认。"""
    try:
        answer = input("  确认发送？(yes/no): ").strip().lower()
        return answer in ("yes", "y")
    except (EOFError, KeyboardInterrupt):
        # 处理管道输入或 Ctrl+C。
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="使用 QQ 邮箱发送纯文本测试邮件（需手动确认）",
    )
    parser.add_argument(
        "-t", "--to",
        default="1962383827@qq.com",
        help="收件人邮箱地址",
    )
    parser.add_argument(
        "-s", "--subject",
        default="ParamGuard 测试邮件",
        help="邮件主题",
    )
    parser.add_argument(
        "-b", "--body",
        default="这是一封来自 ParamGuard 项目的测试邮件。\n\n如果收到此邮件，说明 QQ 邮箱 SMTP 发送功能正常工作。\n",
        help="邮件正文",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="跳过确认，直接发送",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不发送",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    parser.add_argument(
        "-a", "--attach",
        action="append",
        default=[],
        metavar="PATH",
        help="附件路径（可重复指定，仅允许 tests/ 目录内的文件）",
    )
    args = parser.parse_args()

    to_address = args.to.strip()
    subject = args.subject
    body = args.body
    attachment_paths = args.attach
    # 仅取文件名用于预览（actual 校验在 send_plain_email 中完成）。
    attachment_preview = [Path(p).name for p in attachment_paths]

    # ── 预览 ──────────────────────────────────────────────────
    if not args.json:
        _print_preview(to_address, subject, body, attachment_preview)

    # ── 仅预览模式 ────────────────────────────────────────────
    if args.dry_run:
        print("\n  (dry-run 模式，未实际发送)")
        return 0

    # ── 确认 ──────────────────────────────────────────────────
    if not args.yes:
        confirmed = _prompt_confirm()
        if not confirmed:
            print("\n  已取消发送。")
            from agent.tool_result import ToolResult, ErrorType, write_audit_log
            tr = ToolResult(
                success=False,
                tool_name="send_email",
                params={"to_address": to_address, "subject": subject, "body_length": len(body)},
                result={"to_address": to_address, "subject": subject},
                error_type=ErrorType.VALIDATION,
                error="用户在确认环节取消",
            )
            write_audit_log(tr)
            return 1

    # ── 发送（内容与预览完全一致） ───────────────────────────
    try:
        result = send_plain_email(
            to_address=to_address,
            subject=subject,
            body=body,
            attachments=attachment_paths if attachment_paths else None,
        )

        if args.json:
            import json
            print(json.dumps({
                "success": result.success,
                "tool_name": result.tool_name,
                "params": result.params,
                "result": result.result,
                "error_type": result.error_type,
                "error": result.error,
                "timestamp": result.timestamp,
                "audit_id": result.audit_id,
            }, ensure_ascii=False, indent=2))
        elif result.success:
            print(f"\n  邮件发送成功！收件人: {result.result.get('to_address', '')}")
            att_names = result.result.get("attachment_names", [])
            if att_names:
                print(f"  附件: {', '.join(att_names)}")
        else:
            print(f"\n  邮件发送失败: {result.error}", file=sys.stderr)

        return 0 if result.success else 1

    except Exception as error:
        from agent.tool_result import ToolResult, ErrorType, write_audit_log
        tr = ToolResult(
            success=False,
            tool_name="send_email",
            params={"to_address": to_address, "subject": subject, "body_length": len(body)},
            result={},
            error_type=ErrorType.SYSTEM,
            error=str(error),
        )
        write_audit_log(tr)
        print(f"\n  发送异常: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
