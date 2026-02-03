"""Context management module for self-evaluation system."""

from .models import (
    ExecutionContext,
    IterationRecord,
    ErrorInfo,
    EvaluationResult,
    RevisionAdvice
)

# 延迟导入以避免循环依赖
def _lazy_import():
    """延迟导入避免启动时的依赖问题"""
    global ContextManager, StorageBackend, FileStorageBackend
    from .context_manager import ContextManager
    from .storage import StorageBackend, FileStorageBackend

# 新功能可以直接导入 (不依赖 storage)
from .guard import (
    evaluate_context_window_guard,
    should_compact_history,
    estimate_token_count,
)
from .compaction import (
    compact_history,
    generate_summary,
    generate_simple_summary,
)

# 尝试导入,如果失败则延迟加载
try:
    from .context_manager import ContextManager
    from .storage import StorageBackend, FileStorageBackend
except ImportError:
    # 延迟导入
    ContextManager = None
    StorageBackend = None
    FileStorageBackend = None

__all__ = [
    "ExecutionContext",
    "IterationRecord",
    "ErrorInfo",
    "EvaluationResult",
    "RevisionAdvice",
    "ContextManager",
    "StorageBackend",
    "FileStorageBackend",
    "evaluate_context_window_guard",
    "should_compact_history",
    "estimate_token_count",
    "compact_history",
    "generate_summary",
    "generate_simple_summary",
]
