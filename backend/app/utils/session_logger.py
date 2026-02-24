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
Session Logger - JSONL-based persistent logging for Agent sessions.

Each session is logged to an independent .jsonl file containing:
- All messages (user/assistant)
- All tool calls and results
- All code executions and outputs
- Failover events
- Context compaction events

Directory structure:
backend/logs/sessions/
  ├── user_1/
  │   ├── sess_abc123.jsonl
  │   └── sess_def456.jsonl
  └── default/
      └── ...
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class EventType(str, Enum):
    """Session event type"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CODE_EXECUTION = "code_execution"
    CODE_RESULT = "code_result"
    ERROR = "error"
    CONTEXT_COMPACTION = "context_compaction"
    FAILOVER = "failover"
    STATUS = "status"  # Agent status update


class SessionLogger:
    """
    Session-level logger.
    
    Each session is logged to an independent .jsonl file.
    Uses buffered writes for better performance.
    """
    
    def __init__(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        log_dir: Optional[Path] = None,
        buffer_size: int = 10
    ):
        """
        Initialize SessionLogger.
        
        Args:
            session_id: Session ID
            user_id: User ID (None means default)
            log_dir: Log root directory (default: backend/logs/sessions/)
            buffer_size: Buffer size (writes to disk when this size is reached)
        """
        self.session_id = session_id
        self.user_id = user_id or "default"
        self.buffer_size = buffer_size
        
        # Create log directory
        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / "logs" / "sessions"
        
        self.user_log_dir = log_dir / str(self.user_id)
        self.user_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file path
        self.log_file = self.user_log_dir / f"sess_{session_id}.jsonl"
        
        # Buffer
        self.buffer: List[Dict[str, Any]] = []
        
        # Event counter
        self.event_count = 0
    
    def _write_event(self, event: Dict[str, Any]):
        """
        Write event to buffer.
        
        Args:
            event: Event data
        """
        # Add timestamp
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add event sequence number
        event["seq"] = self.event_count
        self.event_count += 1
        
        # Add to buffer
        self.buffer.append(event)
        
        # Write when buffer size is reached
        if len(self.buffer) >= self.buffer_size:
            self._flush()
    
    def _flush(self):
        """Flush buffer to file"""
        if not self.buffer:
            return
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for event in self.buffer:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            
            self.buffer.clear()
        except Exception as e:
            print(f"[SessionLogger] Failed to flush buffer: {e}")
    
    def log_session_start(
        self, 
        model: str,
        mcp_server_url: Optional[str] = None,
        **kwargs
    ):
        """
        Log session start.
        
        Args:
            model: Model name
            mcp_server_url: MCP server URL
            **kwargs: Additional metadata
        """
        self._write_event({
            "type": EventType.SESSION_START,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model": model,
            "mcp_server_url": mcp_server_url,
            **kwargs
        })
        self._flush()  # Write immediately
    
    def log_message(
        self, 
        role: str, 
        content: str,
        turn: Optional[int] = None,
        **kwargs
    ):
        """
        Log message (user/assistant).
        
        Args:
            role: Role ("user" or "assistant")
            content: Message content
            turn: Conversation turn
            **kwargs: Additional metadata
        """
        event = {
            "type": EventType.MESSAGE,
            "role": role,
            "content": content,
            **kwargs
        }
        
        if turn is not None:
            event["turn"] = turn
        
        self._write_event(event)
    
    def log_tool_call(
        self, 
        tool: str, 
        args: Dict[str, Any], 
        call_id: str,
        turn: Optional[int] = None,
        **kwargs
    ):
        """
        Log tool call.
        
        Args:
            tool: Tool name
            args: Tool arguments
            call_id: Call ID
            turn: Conversation turn
            **kwargs: Additional metadata
        """
        event = {
            "type": EventType.TOOL_CALL,
            "tool": tool,
            "args": args,
            "call_id": call_id,
            **kwargs
        }
        
        if turn is not None:
            event["turn"] = turn
        
        self._write_event(event)
    
    def log_tool_result(
        self, 
        tool: str, 
        call_id: str, 
        status: str, 
        result: Any,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """
        Log tool result.
        
        Args:
            tool: Tool name
            call_id: Call ID
            status: Status ("success" or "error")
            result: Result data
            duration_ms: Execution time (milliseconds)
            **kwargs: Additional metadata
        """
        event = {
            "type": EventType.TOOL_RESULT,
            "tool": tool,
            "call_id": call_id,
            "status": status,
            "result": result,
            **kwargs
        }
        
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        
        self._write_event(event)
    
    def log_code_execution(
        self, 
        code: str,
        turn: Optional[int] = None,
        **kwargs
    ):
        """
        Log code execution.
        
        Args:
            code: Code content
            turn: Conversation turn
            **kwargs: Additional metadata
        """
        event = {
            "type": EventType.CODE_EXECUTION,
            "code": code,
            **kwargs
        }
        
        if turn is not None:
            event["turn"] = turn
        
        self._write_event(event)
    
    def log_code_result(
        self, 
        status: str, 
        stdout: str = "", 
        stderr: str = "", 
        output_files: Optional[List[str]] = None,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """
        Log code execution result.
        
        Args:
            status: Status ("success" or "error")
            stdout: Standard output
            stderr: Standard error
            output_files: List of generated files
            duration_ms: Execution time (milliseconds)
            **kwargs: Additional metadata
        """
        event = {
            "type": EventType.CODE_RESULT,
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "output_files": output_files or [],
            **kwargs
        }
        
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        
        self._write_event(event)
    
    def log_error(
        self, 
        error: str,
        error_type: Optional[str] = None,
        turn: Optional[int] = None,
        **kwargs
    ):
        """
        Log error.
        
        Args:
            error: Error message
            error_type: Error type
            turn: Conversation turn
            **kwargs: Additional metadata
        """
        event = {
            "type": EventType.ERROR,
            "error": error,
            **kwargs
        }
        
        if error_type:
            event["error_type"] = error_type
        
        if turn is not None:
            event["turn"] = turn
        
        self._write_event(event)
    
    def log_context_compaction(
        self, 
        messages_before: int, 
        messages_after: int,
        strategy: str = "auto",
        **kwargs
    ):
        """
        Log context compaction.
        
        Args:
            messages_before: Message count before compaction
            messages_after: Message count after compaction
            strategy: Compaction strategy
            **kwargs: Additional metadata
        """
        self._write_event({
            "type": EventType.CONTEXT_COMPACTION,
            "messages_before": messages_before,
            "messages_after": messages_after,
            "strategy": strategy,
            **kwargs
        })
    
    def log_failover(
        self, 
        layer: str, 
        from_value: str, 
        to_value: str, 
        reason: str,
        **kwargs
    ):
        """
        Log failover.
        
        Args:
            layer: Failover layer ("auth", "model", "thinking")
            from_value: Original value
            to_value: Target value
            reason: Failover reason
            **kwargs: Additional metadata
        """
        self._write_event({
            "type": EventType.FAILOVER,
            "layer": layer,
            "from": from_value,
            "to": to_value,
            "reason": reason,
            **kwargs
        })
    
    def log_status(
        self, 
        content: str,
        turn: Optional[int] = None,
        **kwargs
    ):
        """
        Log status update.
        
        Args:
            content: Status message
            turn: Conversation turn
            **kwargs: Additional metadata
        """
        event = {
            "type": EventType.STATUS,
            "content": content,
            **kwargs
        }
        
        if turn is not None:
            event["turn"] = turn
        
        self._write_event(event)
    
    def log_session_end(
        self, 
        status: str, 
        total_turns: int,
        total_events: Optional[int] = None,
        **kwargs
    ):
        """
        Log session end.
        
        Args:
            status: End status ("success", "error", "cancelled")
            total_turns: Total conversation turns
            total_events: Total event count
            **kwargs: Additional metadata
        """
        self._write_event({
            "type": EventType.SESSION_END,
            "status": status,
            "total_turns": total_turns,
            "total_events": total_events or self.event_count,
            **kwargs
        })
        self._flush()  # Write immediately
    
    def close(self):
        """Close logger, flush buffer"""
        self._flush()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.close()
        return False

