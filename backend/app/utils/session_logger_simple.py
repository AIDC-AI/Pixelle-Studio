"""
Simplified session logger.
Records all conversation session events to JSONL format files.
"""
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, Optional


class SessionLogger:
    """Session logger"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        """
        Initialize session logger.
        
        Args:
            session_id: Session ID
            user_id: User ID (optional)
        """
        self.session_id = session_id
        self.user_id = user_id or "default"
        
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
    
    def log_session_end(self, status: str, total_turns: int):
        """Log session end"""
        self._write_event("session_end", {
            "status": status,
            "total_turns": total_turns
        })
    
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

