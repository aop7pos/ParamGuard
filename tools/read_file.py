"""读取指定文件内容的命令行工具。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 确保直接运行脚本时也能找到项目内的 agent 包。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.file_reader import read_file_content
from agent.logger import log_file_read


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
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        help="以 JSON 格式输出完整结果（包含路径、内容、执行状态）",
    )
    args = parser.parse_args()

    try:
        result = read_file_content(args.path, encoding=args.encoding)
        if result.success:
            if args.json:
                import json
                print(json.dumps({
                    "path": result.path,
                    "content": result.content,
                    "success": result.success,
                    "error": result.error,
                }, ensure_ascii=False, indent=2))
            else:
                # end="" 避免 print 再添加换行符，从而保持文件内容原样输出。
                print(result.content, end="")
        else:
            if args.json:
                import json
                print(json.dumps({
                    "path": result.path,
                    "content": result.content,
                    "success": result.success,
                    "error": result.error,
                }, ensure_ascii=False, indent=2), file=sys.stderr)
            else:
                print(f"读取文件失败: {result.error}", file=sys.stderr)
            return 1
    except Exception as error:
        # 捕获所有未预期的异常（如系统级错误），使用标准错误流输出。
        log_file_read(path=args.path, success=False, error=str(error))
        print(f"读取文件失败: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    # 让脚本退出状态码可被 PowerShell、CI 等调用者正确识别。
    raise SystemExit(main())
