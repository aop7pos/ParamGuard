"""ParamGuard 的通用工具模块。"""

from .file_reader import read_file_content
from .file_searcher import SearchMatch, SearchResult, search_files

__all__ = ["read_file_content", "search_files", "SearchMatch", "SearchResult"]
