"""提供读取指定文本文件内容的功能。"""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from pathlib import Path

# 项目根目录，用于限定可读取的文件范围。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 仅允许读取该目录下的文件。
_ALLOWED_DIR = _PROJECT_ROOT / "tests"


@dataclass
class ReadResult:
    """文件读取的执行结果。

    Attributes:
        path: 解析后的文件绝对路径。
        content: 文件内容，失败时为空字符串。
        success: 是否读取成功。
        error: 失败时的错误信息，成功时为空字符串。
    """
    path: str
    content: str
    success: bool
    error: str


def read_file_content(path: str | PathLike[str], *, encoding: str = "utf-8") -> ReadResult:
    """读取指定文本文件，返回包含路径、内容和执行结果的 ``ReadResult``。

    **只允许读取 ``tests/`` 目录下的文件**。所有错误均封装在返回值的
    ``success`` 与 ``error`` 字段中，不再抛出异常。

    Args:
        path: 待读取文件的路径，支持字符串或 ``pathlib.Path`` 对象。
        encoding: 文件的文本编码，默认使用 UTF-8。

    Returns:
        ``ReadResult``，包含文件路径、内容、成功标志和错误信息。
    """
    # 空字符串路径通常意味着调用方漏传参数。
    if isinstance(path, str):
        if not path.strip():
            return ReadResult(path="", content="", success=False, error="文件路径不能为空")
        # 路径中包含空字节（\0）属于非法输入，常见于恶意构造的截断攻击。
        if "\0" in path:
            return ReadResult(path=path, content="", success=False, error="文件路径包含非法字符（空字节）")
        file_path = Path(path)
    elif isinstance(path, PathLike):
        file_path = Path(path)
    else:
        return ReadResult(path=str(path), content="", success=False, error="文件路径必须是字符串或路径对象")

    # 解析为绝对路径，防止相对路径或符号链接绕过目录检查。
    resolved = file_path.resolve()

    # 只允许读取 tests/ 目录下的文件，任何越权尝试均拒绝。
    try:
        resolved.relative_to(_ALLOWED_DIR.resolve())
    except ValueError:
        return ReadResult(
            path=str(resolved), content="", success=False,
            error=f"不允许读取该路径（试图访问 tests/ 目录之外的文件）: {file_path}",
        )

    # 目录不能作为文本文件读取。
    if resolved.is_dir():
        return ReadResult(
            path=str(resolved), content="", success=False,
            error=f"指定路径是目录，无法读取文件内容: {file_path}",
        )

    # 文件不存在时给出清晰的错误信息。
    if not resolved.is_file():
        return ReadResult(
            path=str(resolved), content="", success=False,
            error=f"文件不存在: {file_path}",
        )

    # 实际读取文件，将解码、权限等系统错误也封装进结果。
    try:
        content = resolved.read_text(encoding=encoding)
    except (OSError, UnicodeError) as exc:
        return ReadResult(
            path=str(resolved), content="", success=False,
            error=f"读取文件失败: {exc}",
        )

    return ReadResult(path=str(resolved), content=content, success=True, error="")
