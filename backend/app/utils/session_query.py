"""
Session Query - Tools for querying and analyzing session logs.

Provides APIs to:
- List all sessions
- Get complete event stream for a session
- Extract conversation history
- Query tool call records
- Query code execution records
- Statistical analysis
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class SessionQuery:
    """Tool class for querying session logs"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize SessionQuery.
        
        Args:
            log_dir: Log root directory (default: backend/logs/sessions/)
        """
        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / "logs" / "sessions"
        self.log_dir = Path(log_dir)
    
    def list_sessions(
        self, 
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all sessions.
        
        Args:
            user_id: Filter by user (None means all users)
            limit: Limit return count
            status: Filter by status ("success", "error", "running")
        
        Returns:
            Session list (sorted by start time descending)
        """
        sessions = []
        
        if not self.log_dir.exists():
            return []
        
        # Determine user directories to scan
        if user_id:
            user_dirs = [self.log_dir / str(user_id)]
        else:
            user_dirs = [d for d in self.log_dir.iterdir() if d.is_dir()]
        
        for user_dir in user_dirs:
            if not user_dir.exists():
                continue
            
            for log_file in user_dir.glob("sess_*.jsonl"):
                try:
                    session_id = log_file.stem.replace("sess_", "")
                    
                    # Read first and last lines
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    if not lines:
                        continue
                    
                    # Parse first line (session_start)
                    start_event = json.loads(lines[0])
                    
                    # Parse last line (may be session_end)
                    end_event = None
                    if len(lines) > 1:
                        try:
                            end_event = json.loads(lines[-1])
                            if end_event.get("type") != "session_end":
                                end_event = None
                        except:
                            pass
                    
                    session_status = "running"
                    if end_event:
                        session_status = end_event.get("status", "unknown")
                    
                    # Filter by status
                    if status and session_status != status:
                        continue
                    
                    sessions.append({
                        "session_id": session_id,
                        "user_id": user_dir.name,
                        "start_time": start_event.get("timestamp"),
                        "end_time": end_event.get("timestamp") if end_event else None,
                        "status": session_status,
                        "total_turns": end_event.get("total_turns") if end_event else None,
                        "total_events": end_event.get("total_events") if end_event else len(lines),
                        "model": start_event.get("model"),
                        "log_file": str(log_file)
                    })
                except Exception as e:
                    print(f"[SessionQuery] Error reading session file {log_file}: {e}")
                    continue
        
        # Sort by start time (newest first)
        sessions.sort(key=lambda s: s["start_time"] or "", reverse=True)
        
        # Limit count
        if limit:
            sessions = sessions[:limit]
        
        return sessions
    
    def get_session_events(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all events for a session.
        
        Args:
            session_id: Session ID
            user_id: User ID (None means search all users)
            event_type: Filter by event type
        
        Returns:
            Event list
        """
        log_file = self._find_log_file(session_id, user_id)
        if not log_file:
            return []
        
        events = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    
                    # Filter by event type
                    if event_type and event.get("type") != event_type:
                        continue
                    
                    events.append(event)
                except json.JSONDecodeError:
                    continue
        
        return events
    
    def get_conversation_history(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        include_timestamps: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history (messages only).
        
        Args:
            session_id: Session ID
            user_id: User ID
            include_timestamps: Whether to include timestamps
        
        Returns:
            Message list
        """
        events = self.get_session_events(session_id, user_id, event_type="message")
        
        messages = []
        for event in events:
            msg = {
                "role": event["role"],
                "content": event["content"]
            }
            
            if include_timestamps:
                msg["timestamp"] = event.get("timestamp")
                msg["turn"] = event.get("turn")
            
            messages.append(msg)
        
        return messages
    
    def get_tool_calls(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all tool calls and their results.
        
        Args:
            session_id: Session ID
            user_id: User ID
            tool_name: Filter by tool name
        
        Returns:
            Tool call list (including results)
        """
        # Get all tool_call and tool_result events
        call_events = self.get_session_events(session_id, user_id, event_type="tool_call")
        result_events = self.get_session_events(session_id, user_id, event_type="tool_result")
        
        # Build call_id -> result mapping
        results_map = {e["call_id"]: e for e in result_events}
        
        tool_calls = []
        for call_event in call_events:
            # Filter by tool name
            if tool_name and call_event.get("tool") != tool_name:
                continue
            
            call_id = call_event["call_id"]
            result_event = results_map.get(call_id)
            
            tool_calls.append({
                "tool": call_event["tool"],
                "args": call_event["args"],
                "call_id": call_id,
                "timestamp": call_event.get("timestamp"),
                "turn": call_event.get("turn"),
                "result": result_event.get("result") if result_event else None,
                "status": result_event.get("status") if result_event else None,
                "duration_ms": result_event.get("duration_ms") if result_event else None
            })
        
        return tool_calls
    
    def get_code_executions(
        self, 
        session_id: str, 
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all code executions and their results.
        
        Args:
            session_id: Session ID
            user_id: User ID
        
        Returns:
            Code execution list (including results)
        """
        # Get all code_execution and code_result events
        exec_events = self.get_session_events(session_id, user_id, event_type="code_execution")
        result_events = self.get_session_events(session_id, user_id, event_type="code_result")
        
        # Assume code_execution and code_result are paired in order
        executions = []
        result_idx = 0
        
        for exec_event in exec_events:
            result_event = None
            if result_idx < len(result_events):
                # Find next code_result
                result_event = result_events[result_idx]
                result_idx += 1
            
            executions.append({
                "code": exec_event["code"],
                "timestamp": exec_event.get("timestamp"),
                "turn": exec_event.get("turn"),
                "status": result_event.get("status") if result_event else None,
                "stdout": result_event.get("stdout", "") if result_event else "",
                "stderr": result_event.get("stderr", "") if result_event else "",
                "output_files": result_event.get("output_files", []) if result_event else [],
                "duration_ms": result_event.get("duration_ms") if result_event else None
            })
        
        return executions
    
    def get_failovers(
        self, 
        session_id: str, 
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all failover events.
        
        Args:
            session_id: Session ID
            user_id: User ID
        
        Returns:
            Failover list
        """
        return self.get_session_events(session_id, user_id, event_type="failover")
    
    def get_session_stats(
        self, 
        session_id: str, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Args:
            session_id: Session ID
            user_id: User ID
        
        Returns:
            Statistics dictionary
        """
        events = self.get_session_events(session_id, user_id)
        
        if not events:
            return {}
        
        # Basic info
        start_event = events[0]
        end_event = events[-1] if events[-1].get("type") == "session_end" else None
        
        # Count events by type
        event_counts = {}
        for event in events:
            event_type = event.get("type")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Tool usage statistics
        tool_usage = {}
        for event in events:
            if event.get("type") == "tool_call":
                tool = event.get("tool")
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        # Code execution statistics
        code_executions = event_counts.get("code_execution", 0)
        code_success = len([e for e in events if e.get("type") == "code_result" and e.get("status") == "success"])
        code_errors = len([e for e in events if e.get("type") == "code_result" and e.get("status") == "error"])
        
        # Failover statistics
        failovers = event_counts.get("failover", 0)
        
        stats = {
            "session_id": session_id,
            "start_time": start_event.get("timestamp"),
            "end_time": end_event.get("timestamp") if end_event else None,
            "status": end_event.get("status") if end_event else "running",
            "total_events": len(events),
            "total_turns": end_event.get("total_turns") if end_event else None,
            "model": start_event.get("model"),
            "event_counts": event_counts,
            "tool_usage": tool_usage,
            "code_stats": {
                "total_executions": code_executions,
                "successful": code_success,
                "errors": code_errors,
                "success_rate": f"{code_success / code_executions * 100:.1f}%" if code_executions > 0 else "N/A"
            },
            "failovers": failovers
        }
        
        return stats
    
    def search_sessions(
        self, 
        keyword: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search sessions containing keyword.
        
        Args:
            keyword: Search keyword
            user_id: Filter by user
            limit: Limit return count
        
        Returns:
            Matching session list
        """
        all_sessions = self.list_sessions(user_id=user_id)
        
        matches = []
        for session in all_sessions:
            # Get conversation history
            conversation = self.get_conversation_history(session["session_id"], session["user_id"])
            
            # Check if contains keyword
            found = False
            for msg in conversation:
                if keyword.lower() in msg["content"].lower():
                    found = True
                    break
            
            if found:
                matches.append({
                    **session,
                    "matched_messages": [
                        msg for msg in conversation 
                        if keyword.lower() in msg["content"].lower()
                    ][:3]  # Only return first 3 matching messages
                })
            
            if len(matches) >= limit:
                break
        
        return matches
    
    def _find_log_file(self, session_id: str, user_id: Optional[str] = None) -> Optional[Path]:
        """
        Find session log file.
        
        Args:
            session_id: Session ID
            user_id: User ID (None means search all users)
        
        Returns:
            Log file path, or None if not found
        """
        if user_id:
            log_file = self.log_dir / str(user_id) / f"sess_{session_id}.jsonl"
            if log_file.exists():
                return log_file
            return None
        
        # Search all user directories
        for user_dir in self.log_dir.iterdir():
            if not user_dir.is_dir():
                continue
            log_file = user_dir / f"sess_{session_id}.jsonl"
            if log_file.exists():
                return log_file
        
        return None

