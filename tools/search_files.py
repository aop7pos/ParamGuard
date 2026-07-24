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
                "query": result.query,
                "search_dir": result.search_dir,
                "matches": [
                    {
                        "file_path": m.file_path,
                        "file_name": m.file_name,
                        "match_type": m.match_type,
                        "snippet": m.snippet,
                    }
                    for m in result.matches
                ],
                "total_files_scanned": result.total_files_scanned,
                "total_files_skipped": result.total_files_skipped,
                "errors": result.errors,
            }, ensure_ascii=False, indent=2))
        else:
            if not result.matches:
                print(f"未找到匹配 \"{result.query}\" 的文件")
            else:
                for i, match in enumerate(result.matches, 1):
                    tag = "[文件名]" if match.match_type == "filename" else "[内容]"
                    print(f"{i}. {tag} {match.file_name}")
                    print(f"   路径: {match.file_path}")
                    if match.match_type == "content":
                        print(f"   片段: {match.snippet}")
                    print()

            if result.errors:
                print(f"--- 跳过 {result.total_files_skipped} 个文件 ---", file=sys.stderr)
                for err in result.errors:
                    print(f"  {err}", file=sys.stderr)

        if result.errors:
            return 1 if not result.matches else 0
        return 0

    except Exception as error:
        from agent.logger import log_file_search
        log_file_search(
            query=args.query,
            search_dir=args.dir or "",
            match_count=0,
            files_scanned=0,
            files_skipped=0,
            errors=[str(error)],
        )
        print(f"搜索失败: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
