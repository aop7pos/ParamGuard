"""发送测试邮件的命令行工具。

**必须手动触发，不会自动执行。**
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.email_sender import send_plain_email


def main() -> int:
    parser = argparse.ArgumentParser(description="使用 QQ 邮箱发送纯文本测试邮件")
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
        "-j", "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    args = parser.parse_args()

    try:
        result = send_plain_email(
            to_address=args.to,
            subject=args.subject,
            body=args.body,
        )

        if args.json:
            import json
            print(json.dumps({
                "to_address": result.to_address,
                "subject": result.subject,
                "success": result.success,
                "error": result.error,
            }, ensure_ascii=False, indent=2))
        elif result.success:
            print(f"邮件发送成功！收件人: {result.to_address}")
        else:
            print(f"邮件发送失败: {result.error}", file=sys.stderr)

        return 0 if result.success else 1

    except Exception as error:
        from agent.logger import log_email_send
        log_email_send(to_address=args.to, subject=args.subject, success=False, error=str(error))
        print(f"发送异常: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
