"""读取指定文件内容的命令行工具。"""

from __future__ import annotations

import argparse
import sys

from agent.file_reader import read_file_content


def main() -> int:
    """解析命令行参数，读取文件并将内容输出到终端。"""
    # 使用 argparse 让路径和编码参数具备自动生成的帮助说明。
    parser = argparse.ArgumentParser(description="读取并输出指定文本文件的完整内容")
    parser.add_argument("path", help="要读取的文件路径")
    parser.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
        help="文件编码，默认是 utf-8",
    )
    args = parser.parse_args()

    try:
        # end="" 避免 print 再添加换行符，从而保持文件内容原样输出。
        print(read_file_content(args.path, encoding=args.encoding), end="")
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        # 预期的输入与文件错误使用标准错误流输出，并以非零状态码结束。
        print(f"读取文件失败: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    # 让脚本退出状态码可被 PowerShell、CI 等调用者正确识别。
    raise SystemExit(main())
