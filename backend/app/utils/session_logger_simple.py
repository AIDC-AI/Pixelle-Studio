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

"""
Simplified session logger.
Records all conversation session events to JSONL format files.
Includes LLM token usage tracking and cost estimation.
"""
from pathlib import Path
from datetime import datetime
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Model pricing (USD per 1M tokens) - Updated 2025
# ============================================================================
MODEL_PRICING = {
    # OpenAI models
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Claude models
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "us.anthropic.claude-sonnet-4-20250514-v1:0": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # DeepSeek models
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}

# Default pricing if model not found (use GPT-4o pricing as safe estimate)
DEFAULT_PRICING = {"input": 2.50, "output": 10.00}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate cost in USD based on model and token counts.
    
    Args:
        model: Model name
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens
    
    Returns:
        Estimated cost in USD
    """
    # Try exact match first, then prefix match
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Try prefix matching (e.g., "gpt-4o-2024-01-01" matches "gpt-4o")
        for model_prefix, price in MODEL_PRICING.items():
            if model.startswith(model_prefix):
                pricing = price
                break
    
    if not pricing:
        pricing = DEFAULT_PRICING
    
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class SessionLogger:
    """Session logger with token usage and cost tracking"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        """
        Initialize session logger.
        
        Args:
            session_id: Session ID
            user_id: User ID (optional)
        """
        self.session_id = session_id
        self.user_id = user_id or "default"
        
        # Token usage accumulator for the session
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.llm_call_count = 0
        
        # Create log directory
        log_dir = Path(__file__).parent.parent.parent / "logs" / "sessions" / self.user_id
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file path
        self.log_file = log_dir / f"sess_{session_id}.jsonl"
        
        # Open file handle (append mode)
        self.file_handle = open(self.log_file, "a", encoding="utf-8")
    
    def _write_event(self, event_type: str, data: Dict[str, Any], turn: Optional[int] = None):
        """
        Write event to log file.
        
        Args:
            event_type: Event type
            data: Event data
            turn: Turn number (optional)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "event_type": event_type,
            "turn": turn,
            **data
        }
        self.file_handle.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        self.file_handle.flush()  # Flush to disk immediately
    
    def log_session_start(self, model: str, mcp_server_url: Optional[str] = None):
        """Log session start"""
        self._write_event("session_start", {
            "model": model,
            "mcp_server_url": mcp_server_url
        })
    
    def log_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int = None,
        call_type: str = "chat",
        turn: Optional[int] = None
    ):
        """
        Log LLM token usage and estimated cost.
        
        Args:
            model: Model name used
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            total_tokens: Total tokens (if not provided, calculated from prompt + completion)
            call_type: Type of LLM call (e.g., "chat", "script_gen", "summary", "title_gen")
            turn: Turn number (optional)
        """
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
        
        cost = estimate_cost(model, prompt_tokens, completion_tokens)
        
        # Accumulate session totals
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += cost
        self.llm_call_count += 1
        
        self._write_event("llm_usage", {
            "model": model,
            "call_type": call_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": cost,
            "session_cumulative": {
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
                "total_cost_usd": round(self.total_cost, 6),
                "llm_call_count": self.llm_call_count
            }
        }, turn=turn)
        
        # Also log to standard logger for easy monitoring
        logger.info(
            f"[TokenUsage][{call_type}] model={model} "
            f"prompt={prompt_tokens} completion={completion_tokens} total={total_tokens} "
            f"cost=${cost:.6f} | "
            f"session_total: calls={self.llm_call_count} tokens={self.total_prompt_tokens + self.total_completion_tokens} cost=${self.total_cost:.6f}"
        )
    
    def log_session_end(self, status: str, total_turns: int):
        """Log session end with token usage summary"""
        self._write_event("session_end", {
            "status": status,
            "total_turns": total_turns,
            "token_usage_summary": {
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
                "total_cost_usd": round(self.total_cost, 6),
                "llm_call_count": self.llm_call_count
            }
        })
        
        # Log session summary to standard logger
        logger.info(
            f"[SessionEnd] session={self.session_id} status={status} turns={total_turns} | "
            f"LLM calls={self.llm_call_count} "
            f"prompt_tokens={self.total_prompt_tokens} "
            f"completion_tokens={self.total_completion_tokens} "
            f"total_tokens={self.total_prompt_tokens + self.total_completion_tokens} "
            f"total_cost=${self.total_cost:.6f}"
        )
    
    def log_message(self, role: str, content: str, turn: Optional[int] = None):
        """Log message"""
        self._write_event("message", {
            "role": role,
            "content": content
        }, turn=turn)
    
    def log_status(self, status: str, turn: Optional[int] = None):
        """Log status"""
        self._write_event("status", {
            "status": status
        }, turn=turn)
    
    def log_tool_call(self, tool: str, args: Dict[str, Any], call_id: str, turn: Optional[int] = None):
        """Log tool call"""
        self._write_event("tool_call", {
            "tool": tool,
            "args": args,
            "call_id": call_id
        }, turn=turn)
    
    def log_tool_result(self, tool: str, call_id: str, status: str, result: str, duration_ms: float, turn: Optional[int] = None):
        """Log tool result"""
        self._write_event("tool_result", {
            "tool": tool,
            "call_id": call_id,
            "status": status,
            "result": result[:500],  # Only log first 500 chars
            "duration_ms": duration_ms
        }, turn=turn)
    
    def log_code_execution(self, code: str, turn: Optional[int] = None):
        """Log code execution"""
        self._write_event("code_execution", {
            "code": code
        }, turn=turn)
    
    def log_code_result(self, status: str, stdout: str, stderr: str, output_files: list, duration_ms: float):
        """Log code execution result"""
        self._write_event("code_result", {
            "status": status,
            "stdout": stdout[:500],  # Only log first 500 chars
            "stderr": stderr[:500],
            "output_files": output_files,
            "duration_ms": duration_ms
        })
    
    def log_context_compaction(self, messages_before: int, messages_after: int):
        """Log context compaction"""
        self._write_event("context_compaction", {
            "messages_before": messages_before,
            "messages_after": messages_after
        })
    
    def log_error(self, error: str, error_type: str = "Unknown", turn: Optional[int] = None):
        """Log error"""
        self._write_event("error", {
            "error": error,
            "error_type": error_type
        }, turn=turn)
    
    def close(self):
        """Close log file"""
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
    
    def __del__(self):
        """Destructor, ensure file is closed"""
        self.close()

