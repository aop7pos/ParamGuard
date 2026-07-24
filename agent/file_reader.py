"""提供读取指定文本文件内容的功能。"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

# 项目根目录，用于限定可读取的文件范围。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 仅允许读取该目录下的文件。
_ALLOWED_DIR = _PROJECT_ROOT / "tests"


def read_file_content(path: str | PathLike[str], *, encoding: str = "utf-8") -> str:
    """读取指定文本文件，并返回完整内容。

    **只允许读取 ``tests/`` 目录下的文件**，读取其他路径会抛出 ``ValueError``。

    Args:
        path: 待读取文件的路径，支持字符串或 ``pathlib.Path`` 对象。
        encoding: 文件的文本编码，默认使用 UTF-8。

    Returns:
        文件解码后的完整文本内容，保留原始换行符。

    Raises:
        TypeError: ``path`` 不是字符串或路径对象时抛出。
        ValueError: 路径为空、路径指向目录，或路径不在允许的 ``tests/`` 目录内时抛出。
        FileNotFoundError: 指定文件不存在时抛出。
        UnicodeError: 文件无法用指定编码解码时抛出。
        OSError: 没有读取权限等其他文件系统错误时抛出。
    """
    # 空字符串路径通常意味着调用方漏传参数，提前报错以便定位问题。
    if isinstance(path, str):
        if not path.strip():
            raise ValueError("文件路径不能为空")
        # 路径中包含空字节（\0）属于非法输入，常见于恶意构造的截断攻击。
        if "\0" in path:
            raise ValueError("文件路径包含非法字符（空字节）")
        file_path = Path(path)
    elif isinstance(path, PathLike):
        # PathLike 统一转换为 Path，便于后续进行文件类型判断和读取。
        file_path = Path(path)
    else:
        raise TypeError("文件路径必须是字符串或路径对象")

    # 解析为绝对路径，防止相对路径或符号链接绕过目录检查。
    resolved = file_path.resolve()

    # 只允许读取 tests/ 目录下的文件，任何越权尝试均拒绝。
    try:
        resolved.relative_to(_ALLOWED_DIR.resolve())
    except ValueError:
        raise ValueError(
            f"不允许读取该路径（试图访问 tests/ 目录之外的文件）: {file_path}"
        ) from None

    # read_text 对目录的报错依赖操作系统；此处统一成明确的参数错误信息。
    if resolved.is_dir():
        raise ValueError(f"指定路径是目录，无法读取文件内容: {file_path}")

    # 文件不存在时给出清晰的中文错误信息，而不是依赖 pathlib 的英文异常。
    if not resolved.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # pathlib 会自动关闭文件句柄，并将权限、解码等异常原样交给调用方处理。
    return resolved.read_text(encoding=encoding)
