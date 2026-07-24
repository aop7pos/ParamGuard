"""提供读取指定文本文件内容的功能。"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from .tool_result import ErrorType, ToolResult, write_audit_log

# 项目根目录，用于限定可读取的文件范围。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 仅允许读取该目录下的文件。
_ALLOWED_DIR = _PROJECT_ROOT / "tests"


def _make_result(
    *,
    path: str,
    content: str,
    success: bool,
    error: str,
    error_type: str,
    encoding: str,
) -> ToolResult:
    """构造统一的 ToolResult，同时写入审计日志。"""
    params = {"path": path, "encoding": encoding}
    result = ToolResult(
        success=success,
        tool_name="read_file",
        params=params,
        result={
            "path": path,
            "content": content,
        },
        error_type=error_type,
        error=error,
    )
    write_audit_log(result)
    return result


def read_file_content(path: str | PathLike[str], *, encoding: str = "utf-8") -> ToolResult:
    """读取指定文本文件，返回统一的 ``ToolResult``。

    **只允许读取 ``tests/`` 目录下的文件**。所有错误均封装在返回值的
    ``success`` 与 ``error`` 字段中，不再抛出异常。

    Args:
        path: 待读取文件的路径，支持字符串或 ``pathlib.Path`` 对象。
        encoding: 文件的文本编码，默认使用 UTF-8。

    Returns:
        ``ToolResult``，包含统一的执行状态、参数、结果和审计信息。
    """
    # 空字符串路径通常意味着调用方漏传参数。
    if isinstance(path, str):
        if not path.strip():
            return _make_result(
                path="", content="", success=False,
                error="文件路径不能为空", error_type=ErrorType.VALIDATION,
                encoding=encoding,
            )
        # 路径中包含空字节（\0）属于非法输入，常见于恶意构造的截断攻击。
        if "\0" in path:
            return _make_result(
                path=path, content="", success=False,
                error="文件路径包含非法字符（空字节）", error_type=ErrorType.VALIDATION,
                encoding=encoding,
            )
        file_path = Path(path)
    elif isinstance(path, PathLike):
        file_path = Path(path)
    else:
        return _make_result(
            path=str(path), content="", success=False,
            error="文件路径必须是字符串或路径对象", error_type=ErrorType.VALIDATION,
            encoding=encoding,
        )

    # 解析为绝对路径，防止相对路径或符号链接绕过目录检查。
    resolved = file_path.resolve()

    # 只允许读取 tests/ 目录下的文件，任何越权尝试均拒绝。
    try:
        resolved.relative_to(_ALLOWED_DIR.resolve())
    except ValueError:
        return _make_result(
            path=str(resolved), content="", success=False,
            error=f"不允许读取该路径（试图访问 tests/ 目录之外的文件）: {file_path}",
            error_type=ErrorType.PERMISSION,
            encoding=encoding,
        )

    # 目录不能作为文本文件读取。
    if resolved.is_dir():
        return _make_result(
            path=str(resolved), content="", success=False,
            error=f"指定路径是目录，无法读取文件内容: {file_path}",
            error_type=ErrorType.VALIDATION,
            encoding=encoding,
        )

    # 文件不存在时给出清晰的错误信息。
    if not resolved.is_file():
        return _make_result(
            path=str(resolved), content="", success=False,
            error=f"文件不存在: {file_path}",
            error_type=ErrorType.SYSTEM,
            encoding=encoding,
        )

    # 实际读取文件，将解码、权限等系统错误也封装进结果。
    try:
        content = resolved.read_text(encoding=encoding)
    except (OSError, UnicodeError) as exc:
        return _make_result(
            path=str(resolved), content="", success=False,
            error=f"读取文件失败: {exc}",
            error_type=ErrorType.SYSTEM,
            encoding=encoding,
        )

    return _make_result(
        path=str(resolved), content=content, success=True,
        error="", error_type="",
        encoding=encoding,
    )
