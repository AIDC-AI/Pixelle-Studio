"""Context management module for self-evaluation system."""

from .models import (
    ExecutionContext,
    IterationRecord,
    ErrorInfo,
    EvaluationResult,
    RevisionAdvice
)
from .context_manager import ContextManager
from .storage import StorageBackend, FileStorageBackend

__all__ = [
    "ExecutionContext",
    "IterationRecord",
    "ErrorInfo",
    "EvaluationResult",
    "RevisionAdvice",
    "ContextManager",
    "StorageBackend",
    "FileStorageBackend"
]
