"""Context manager for execution history and context summarization."""

from typing import Dict, Optional
from .models import ExecutionContext, IterationRecord
from .storage import StorageBackend, FileStorageBackend


class ContextManager:
    """Manages execution context storage and retrieval."""
    
    def __init__(self, storage_backend: Optional[StorageBackend] = None):
        self.storage = storage_backend or FileStorageBackend()
        # In-memory cache: chat_id -> ExecutionContext
        self.memory_cache: Dict[str, ExecutionContext] = {}
    
    async def initialize_context(
        self,
        chat_id: str,
        user_message: str,
        selected_tools: list,
        max_iterations: int = 3
    ) -> ExecutionContext:
        """Initialize a new execution context."""
        context = ExecutionContext(
            chat_id=chat_id,
            user_message=user_message,
            selected_tools=selected_tools,
            max_iterations=max_iterations,
            current_iteration=0,
            status="initializing"
        )
        
        # Cache in memory
        self.memory_cache[chat_id] = context
        
        # Save metadata to storage
        await self.storage.save_context_metadata(context)
        
        return context
    
    async def store_iteration(
        self,
        chat_id: str,
        iteration_record: IterationRecord
    ) -> None:
        """Store an iteration record."""
        # Update memory cache
        if chat_id in self.memory_cache:
            context = self.memory_cache[chat_id]
            # Check if iteration already exists
            existing_ids = [iter.iteration_id for iter in context.iterations]
            if iteration_record.iteration_id not in existing_ids:
                context.iterations.append(iteration_record)
        
        # Persist to storage
        await self.storage.save_iteration(chat_id, iteration_record)
    
    async def update_context_status(
        self,
        chat_id: str,
        status: str,
        current_iteration: Optional[int] = None
    ) -> None:
        """Update context status and optionally current iteration."""
        if chat_id in self.memory_cache:
            context = self.memory_cache[chat_id]
            context.status = status
            if current_iteration is not None:
                context.current_iteration = current_iteration
            
            # Save metadata
            await self.storage.save_context_metadata(context)
    
    async def get_context(self, chat_id: str) -> Optional[ExecutionContext]:
        """Get execution context (from cache or storage)."""
        # Try memory cache first
        if chat_id in self.memory_cache:
            return self.memory_cache[chat_id]
        
        # Load from storage
        context = await self.storage.load_context(chat_id)
        if context:
            self.memory_cache[chat_id] = context
        
        return context
    
    async def delete_context(self, chat_id: str) -> None:
        """Delete a context from cache and storage."""
        # Remove from cache
        if chat_id in self.memory_cache:
            del self.memory_cache[chat_id]
        
        # Delete from storage
        await self.storage.delete_context(chat_id)
    
    def build_context_summary(
        self,
        context: ExecutionContext,
        max_tokens: int = 2000
    ) -> str:
        """
        Build a context summary for LLM input.
        
        Strategy:
        - Always include: user request, available tools
        - First iteration: no history
        - Subsequent iterations: include previous error, evaluation, and advice
        """
        
        summary_parts = [
            f"User Request: {context.user_message}",
            "",
            f"Available Tools: {', '.join([t['name'] for t in context.selected_tools])}",
            ""
        ]
        
        if context.current_iteration == 0:
            # First attempt
            summary_parts.append("This is the first attempt to generate the script.")
        else:
            # Subsequent iterations
            last_iteration = context.get_latest_iteration()
            
            summary_parts.extend([
                f"This is iteration {context.current_iteration + 1} of {context.max_iterations} (previous attempts failed).",
                ""
            ])
            
            # Previous error
            if last_iteration and last_iteration.error_info:
                error = last_iteration.error_info
                summary_parts.extend([
                    "❌ Previous Error:",
                    f"- Type: {error.error_type}",
                    f"- Message: {error.error_message}",
                    ""
                ])
                
                # Show traceback if available (truncated)
                if error.traceback:
                    traceback_lines = error.traceback.split("\n")
                    if len(traceback_lines) > 5:
                        summary_parts.append("- Traceback (last 5 lines):")
                        for line in traceback_lines[-5:]:
                            summary_parts.append(f"  {line}")
                    else:
                        summary_parts.append("- Traceback:")
                        summary_parts.append(error.traceback)
                    summary_parts.append("")
            
            # Previous evaluation
            if last_iteration and last_iteration.evaluation and not last_iteration.evaluation.meets_requirement:
                eval_result = last_iteration.evaluation
                summary_parts.extend([
                    "⚠️ Previous Validation Failed:",
                    f"- Reason: {eval_result.evaluation_reason}",
                    f"- Missing Aspects: {', '.join(eval_result.missing_aspects)}" if eval_result.missing_aspects else "",
                    ""
                ])
            
            # Revision advice
            if last_iteration and last_iteration.revision_advice:
                advice = last_iteration.revision_advice
                summary_parts.extend([
                    "💡 Revision Advice:",
                    *[f"- {suggestion}" for suggestion in advice.specific_suggestions],
                    ""
                ])
            
            # Summarize all historical errors to avoid repetition
            all_error_types = set()
            for iteration in context.iterations:
                if iteration.error_info:
                    all_error_types.add(iteration.error_info.error_type)
            
            if len(all_error_types) > 1:
                summary_parts.extend([
                    f"⚠️ Historical Errors (avoid repeating): {', '.join(all_error_types)}",
                    ""
                ])
        
        summary = "\n".join(summary_parts)
        
        # Token limit (rough estimation: 1 token ≈ 4 characters)
        max_chars = max_tokens * 4
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n... (truncated due to length)"
        
        return summary
    
    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self.memory_cache.clear()
