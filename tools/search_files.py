"""按文件名或内容关键词搜索文件的命令行工具。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 确保直接运行脚本时也能找到项目内的 agent 包。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.file_searcher import search_files


def main() -> int:
    """解析命令行参数，执行搜索并将结果输出到终端。"""
    parser = argparse.ArgumentParser(
        description="在 tests/ 目录内按文件名或内容关键词搜索文件",
    )
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument(
        "-d", "--dir",
        default=None,
        help="搜索目录，默认为 tests/",
    )
    parser.add_argument(
        "--no-content",
        action="store_true",
        help="不搜索文件内容，仅匹配文件名",
    )
    parser.add_argument(
        "--no-filename",
        action="store_true",
        help="不匹配文件名，仅搜索文件内容",
    )
    parser.add_argument(
        "-e", "--encoding",
        default="utf-8",
        help="文件编码，默认 utf-8",
    )
    parser.add_argument(
        "-c", "--case-sensitive",
        action="store_true",
        help="区分大小写搜索",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="以 JSON 格式输出完整结果",
    )
    args = parser.parse_args()

    try:
        result = search_files(
            args.query,
            search_dir=args.dir,
            search_content=not args.no_content,
            search_filename=not args.no_filename,
            encoding=args.encoding,
            case_sensitive=args.case_sensitive,
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
        else:
            res_data = result.result
            matches = res_data.get("matches", [])
            if not matches:
                print(f"未找到匹配 \"{res_data.get('query', '')}\" 的文件")
            else:
                for i, match in enumerate(matches, 1):
                    tag = "[文件名]" if match["match_type"] == "filename" else "[内容]"
                    print(f"{i}. {tag} {match['file_name']}")
                    print(f"   路径: {match['file_path']}")
                    if match["match_type"] == "content":
                        print(f"   片段: {match['snippet']}")
                    print()

            err_list = res_data.get("errors", [])
            if err_list:
                print(f"--- 跳过 {res_data.get('files_skipped', 0)} 个文件 ---", file=sys.stderr)
                for err in err_list:
                    print(f"  {err}", file=sys.stderr)

        if not result.success or result.result.get("errors"):
            return 1 if not result.result.get("matches") else 0
        return 0

    except Exception as error:
        from agent.tool_result import ToolResult, ErrorType, write_audit_log
        tr = ToolResult(
            success=False,
            tool_name="search_files",
            params={"query": args.query, "search_dir": args.dir or ""},
            result={},
            error_type=ErrorType.SYSTEM,
            error=str(error),
        )
        write_audit_log(tr)
        print(f"搜索失败: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
