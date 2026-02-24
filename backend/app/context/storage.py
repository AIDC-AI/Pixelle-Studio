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

"""Storage backend for execution context persistence."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
import json
import aiofiles
import asyncio

from .models import ExecutionContext, IterationRecord


class StorageBackend(ABC):
    """Abstract storage backend interface."""
    
    @abstractmethod
    async def save_iteration(self, chat_id: str, iteration: IterationRecord) -> None:
        """Save an iteration record."""
        pass
    
    @abstractmethod
    async def save_context_metadata(self, context: ExecutionContext) -> None:
        """Save context metadata (without iterations)."""
        pass
    
    @abstractmethod
    async def load_context(self, chat_id: str) -> Optional[ExecutionContext]:
        """Load complete execution context."""
        pass
    
    @abstractmethod
    async def delete_context(self, chat_id: str) -> None:
        """Delete execution context."""
        pass


class FileStorageBackend(StorageBackend):
    """File-based storage backend using JSON files."""
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # Default to backend/storage/contexts
            base_dir = Path(__file__).parent.parent.parent / "storage" / "contexts"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_context_dir(self, chat_id: str) -> Path:
        """Get directory path for a specific chat context."""
        return self.base_dir / chat_id
    
    def _get_metadata_path(self, chat_id: str) -> Path:
        """Get metadata file path."""
        return self._get_context_dir(chat_id) / "metadata.json"
    
    def _get_iteration_path(self, chat_id: str, iteration_id: int) -> Path:
        """Get iteration file path."""
        return self._get_context_dir(chat_id) / f"iteration_{iteration_id:03d}.json"
    
    async def save_iteration(self, chat_id: str, iteration: IterationRecord) -> None:
        """Save an iteration record to JSON file."""
        context_dir = self._get_context_dir(chat_id)
        context_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = self._get_iteration_path(chat_id, iteration.iteration_id)
        
        # Serialize to JSON
        data = iteration.to_dict()
        
        # Write asynchronously
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    
    async def save_context_metadata(self, context: ExecutionContext) -> None:
        """Save context metadata (user message, tools, config)."""
        context_dir = self._get_context_dir(context.chat_id)
        context_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = self._get_metadata_path(context.chat_id)
        
        # Save only metadata, not iterations
        metadata = {
            "chat_id": context.chat_id,
            "user_message": context.user_message,
            "selected_tools": context.selected_tools,
            "max_iterations": context.max_iterations,
            "current_iteration": context.current_iteration,
            "status": context.status
        }
        
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    async def load_context(self, chat_id: str) -> Optional[ExecutionContext]:
        """Load complete execution context from files."""
        context_dir = self._get_context_dir(chat_id)
        
        if not context_dir.exists():
            return None
        
        # Load metadata
        metadata_path = self._get_metadata_path(chat_id)
        if not metadata_path.exists():
            return None
        
        async with aiofiles.open(metadata_path, "r") as f:
            metadata = json.loads(await f.read())
        
        # Load all iteration records
        iterations = []
        for filepath in sorted(context_dir.glob("iteration_*.json")):
            async with aiofiles.open(filepath, "r") as f:
                iter_data = json.loads(await f.read())
                iteration = IterationRecord.from_dict(iter_data)
                iterations.append(iteration)
        
        # Reconstruct context
        context = ExecutionContext(
            chat_id=metadata["chat_id"],
            user_message=metadata["user_message"],
            selected_tools=metadata["selected_tools"],
            iterations=iterations,
            max_iterations=metadata.get("max_iterations", 3),
            current_iteration=metadata.get("current_iteration", 0),
            status=metadata.get("status", "initializing")
        )
        
        return context
    
    async def delete_context(self, chat_id: str) -> None:
        """Delete all files for a context."""
        context_dir = self._get_context_dir(chat_id)
        
        if context_dir.exists():
            import shutil
            shutil.rmtree(context_dir)
    
    def list_contexts(self) -> list[str]:
        """List all stored context IDs."""
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]
