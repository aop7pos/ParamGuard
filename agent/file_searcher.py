"""在指定目录内按文件名或内容关键词搜索文件的工具。"""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .tool_result import ErrorType, ToolResult, write_audit_log

# 项目根目录，与 file_reader 使用相同的授权目录。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ALLOWED_DIR = _PROJECT_ROOT / "tests"

# 仅处理这些扩展名的文本文件，跳过二进制文件。
_TEXT_EXTENSIONS = {
    ".txt", ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".csv", ".tsv", ".log", ".xml", ".html", ".css", ".js", ".ts", ".sh",
    ".bat", ".ps1", ".rst", ".tex", ".java", ".c", ".h", ".cpp", ".hpp",
    ".rs", ".go", ".rb", ".php", ".sql",
}

# 内容匹配时截取的上下文长度（匹配行的前后字符数）。
_SNIPPET_CONTEXT = 120


@dataclass
class SearchMatch:
    """单条匹配结果。

    Attributes:
        file_path: 匹配文件的绝对路径。
        file_name: 匹配文件的文件名。
        match_type: 匹配类型，``"filename"`` 或 ``"content"``。
        snippet: 命中内容的简短片段。
    """
    file_path: str
    file_name: str
    match_type: str
    snippet: str


def _is_text_file(file_path: Path) -> bool:
    """判断文件是否为可搜索的文本文件。"""
    suffix = file_path.suffix.lower()
    if suffix:
        return suffix in _TEXT_EXTENSIONS
    # 无后缀的文件尝试按文本处理（可能是 Makefile、LICENSE 等）。
    return True


def _extract_snippet(line: str, query: str, case_sensitive: bool) -> str:
    """从匹配行中截取包含关键词的上下文片段。"""
    if not case_sensitive:
        # 在原始行中定位关键词（保留原始大小写）。
        idx = line.lower().find(query.lower())
    else:
        idx = line.find(query)

    if idx == -1:
        # 理论上不会到这里，但做防御性处理：直接截取前段。
        return line[:_SNIPPET_CONTEXT].strip()

    start = max(0, idx - _SNIPPET_CONTEXT // 2)
    end = min(len(line), idx + len(query) + _SNIPPET_CONTEXT // 2)
    snippet = line[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(line):
        snippet = snippet + "…"
    return snippet


def _search_file_content(
    file_path: Path,
    query: str,
    *,
    encoding: str,
    case_sensitive: bool,
) -> tuple[list[SearchMatch], str | None]:
    """在单个文件内容中搜索关键词，返回匹配列表和可能的错误。"""
    try:
        content = file_path.read_text(encoding=encoding)
    except (OSError, UnicodeError) as exc:
        return [], f"无法读取文件 {file_path}: {exc}"

    matches: list[SearchMatch] = []
    search_content = content if case_sensitive else content.lower()
    search_query = query if case_sensitive else query.lower()

    if search_query not in search_content:
        return [], None

    # 逐行查找匹配，每行只记录一次。
    for line in content.splitlines():
        line_query = line if case_sensitive else line.lower()
        if search_query in line_query:
            snippet = _extract_snippet(line, query, case_sensitive)
            matches.append(SearchMatch(
                file_path=str(file_path),
                file_name=file_path.name,
                match_type="content",
                snippet=snippet,
            ))

    return matches, None


def search_files(
    query: str,
    *,
    search_dir: str | PathLike[str] | None = None,
    search_content: bool = True,
    search_filename: bool = True,
    encoding: str = "utf-8",
    case_sensitive: bool = False,
) -> ToolResult:
    """在授权目录内按文件名或内容关键词搜索文件。

    只允许搜索 ``tests/`` 目录下的文件。所有错误均封装在返回值中，
    不抛出异常。没有匹配结果时返回空的 ``matches`` 列表。

    Args:
        query: 搜索关键词，不能为空。
        search_dir: 搜索范围目录，默认为 ``tests/``。
        search_content: 是否搜索文件内容。
        search_filename: 是否搜索文件名。
        encoding: 读取文件内容时使用的编码。
        case_sensitive: 是否区分大小写，默认不区分。

    Returns:
        ``ToolResult``，包含统一的执行状态、参数、结果和审计信息。
    """
    params = {
        "query": query if isinstance(query, str) else str(query),
        "search_dir": str(search_dir) if search_dir else str(_ALLOWED_DIR),
        "search_content": search_content,
        "search_filename": search_filename,
        "encoding": encoding,
        "case_sensitive": case_sensitive,
    }

    def _make(
        *,
        success: bool,
        matches: list[dict] | None = None,
        scanned: int = 0,
        skipped: int = 0,
        err_list: list[str] | None = None,
        error: str = "",
        error_type: str = "",
    ) -> ToolResult:
        tr = ToolResult(
            success=success,
            tool_name="search_files",
            params=params,
            result={
                "query": params["query"],
                "search_dir": params["search_dir"],
                "matches": matches or [],
                "match_count": len(matches) if matches else 0,
                "files_scanned": scanned,
                "files_skipped": skipped,
                "errors": err_list or [],
            },
            error_type=error_type,
            error=error,
        )
        write_audit_log(tr)
        return tr

    # ── 参数校验 ──────────────────────────────────────────────
    if not isinstance(query, str) or not query.strip():
        return _make(
            success=False,
            error="搜索关键词不能为空",
            error_type=ErrorType.VALIDATION,
        )

    query = query.strip()
    params["query"] = query

    # 解析搜索目录。
    if search_dir is None:
        resolved_dir = _ALLOWED_DIR.resolve()
        params["search_dir"] = str(_ALLOWED_DIR)
    elif isinstance(search_dir, (str, PathLike)):
        resolved_dir = Path(str(search_dir)).resolve()
        params["search_dir"] = str(resolved_dir)
    else:
        return _make(
            success=False,
            error="搜索目录必须是字符串或路径对象",
            error_type=ErrorType.VALIDATION,
        )

    # 安全检查：搜索目录必须在授权范围内。
    try:
        resolved_dir.relative_to(_ALLOWED_DIR.resolve())
    except ValueError:
        return _make(
            success=False,
            error=f"不允许搜索该目录（试图访问 tests/ 目录之外的位置）: {search_dir}",
            error_type=ErrorType.PERMISSION,
        )

    # 搜索目录不存在时无结果。
    if not resolved_dir.is_dir():
        return _make(
            success=False,
            error=f"搜索目录不存在: {resolved_dir}",
            error_type=ErrorType.SYSTEM,
        )

    # ── 执行搜索 ──────────────────────────────────────────────
    all_matches: list[SearchMatch] = []
    scanned = 0
    skipped = 0
    err_list: list[str] = []

    for entry in sorted(resolved_dir.rglob("*")):
        # 跳过目录、符号链接等非普通文件。
        if not entry.is_file():
            continue
        # 跳过二进制文件。
        if not _is_text_file(entry):
            continue

        scanned += 1

        # 文件名匹配。
        if search_filename:
            name_to_check = entry.name if case_sensitive else entry.name.lower()
            q_to_check = query if case_sensitive else query.lower()
            if q_to_check in name_to_check:
                all_matches.append(SearchMatch(
                    file_path=str(entry),
                    file_name=entry.name,
                    match_type="filename",
                    snippet=entry.name,
                ))

        # 内容匹配。
        if search_content:
            content_matches, read_error = _search_file_content(
                entry, query, encoding=encoding, case_sensitive=case_sensitive,
            )
            if read_error is not None:
                skipped += 1
                err_list.append(read_error)
            else:
                all_matches.extend(content_matches)

    matches_dicts = [
        {
            "file_path": m.file_path,
            "file_name": m.file_name,
            "match_type": m.match_type,
            "snippet": m.snippet,
        }
        for m in all_matches
    ]

    return _make(
        success=True,
        matches=matches_dicts,
        scanned=scanned,
        skipped=skipped,
        err_list=err_list,
    )
