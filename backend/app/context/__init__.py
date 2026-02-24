# Copyright (C) 2026 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Context management module for self-evaluation system."""

from .models import (
    ExecutionContext,
    IterationRecord,
    ErrorInfo,
    EvaluationResult,
    RevisionAdvice
)

# Lazy import to avoid circular dependencies
def _lazy_import():
    """Lazy import to avoid startup dependency issues"""
    global ContextManager, StorageBackend, FileStorageBackend
    from .context_manager import ContextManager
    from .storage import StorageBackend, FileStorageBackend

# New features can be imported directly (no dependency on storage)
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

# Try to import, fallback to lazy loading on failure
try:
    from .context_manager import ContextManager
    from .storage import StorageBackend, FileStorageBackend
except ImportError:
    # Lazy import
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
