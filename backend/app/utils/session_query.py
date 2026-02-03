"""
Session Query - 查询和分析 Session 日志的工具。

提供 API 来:
- 列出所有 sessions
- 获取 session 的完整事件流
- 提取对话历史
- 查询工具调用记录
- 查询代码执行记录
- 统计分析
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class SessionQuery:
    """查询 session 日志的工具类"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        初始化 SessionQuery。
        
        Args:
            log_dir: 日志根目录 (默认: backend/logs/sessions/)
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
        列出所有 sessions。
        
        Args:
            user_id: 过滤指定用户 (None 表示所有用户)
            limit: 限制返回数量
            status: 过滤指定状态 ("success", "error", "running")
        
        Returns:
            Session 列表 (按开始时间倒序)
        """
        sessions = []
        
        if not self.log_dir.exists():
            return []
        
        # 确定要扫描的用户目录
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
                    
                    # 读取第一行和最后一行
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    if not lines:
                        continue
                    
                    # 解析第一行 (session_start)
                    start_event = json.loads(lines[0])
                    
                    # 解析最后一行 (可能是 session_end)
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
                    
                    # 过滤状态
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
        
        # 按开始时间排序 (最新的在前)
        sessions.sort(key=lambda s: s["start_time"] or "", reverse=True)
        
        # 限制数量
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
        获取 session 的所有事件。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID (None 表示搜索所有用户)
            event_type: 过滤事件类型
        
        Returns:
            事件列表
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
                    
                    # 过滤事件类型
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
        获取对话历史 (只包含消息)。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID
            include_timestamps: 是否包含时间戳
        
        Returns:
            消息列表
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
        获取所有工具调用及其结果。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID
            tool_name: 过滤指定工具
        
        Returns:
            工具调用列表 (包含结果)
        """
        # 获取所有 tool_call 和 tool_result 事件
        call_events = self.get_session_events(session_id, user_id, event_type="tool_call")
        result_events = self.get_session_events(session_id, user_id, event_type="tool_result")
        
        # 构建 call_id -> result 映射
        results_map = {e["call_id"]: e for e in result_events}
        
        tool_calls = []
        for call_event in call_events:
            # 过滤工具名称
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
        获取所有代码执行及其结果。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID
        
        Returns:
            代码执行列表 (包含结果)
        """
        # 获取所有 code_execution 和 code_result 事件
        exec_events = self.get_session_events(session_id, user_id, event_type="code_execution")
        result_events = self.get_session_events(session_id, user_id, event_type="code_result")
        
        # 假设 code_execution 和 code_result 按顺序配对
        executions = []
        result_idx = 0
        
        for exec_event in exec_events:
            result_event = None
            if result_idx < len(result_events):
                # 找到下一个 code_result
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
        获取所有故障转移事件。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID
        
        Returns:
            故障转移列表
        """
        return self.get_session_events(session_id, user_id, event_type="failover")
    
    def get_session_stats(
        self, 
        session_id: str, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取 session 统计信息。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID
        
        Returns:
            统计信息字典
        """
        events = self.get_session_events(session_id, user_id)
        
        if not events:
            return {}
        
        # 基本信息
        start_event = events[0]
        end_event = events[-1] if events[-1].get("type") == "session_end" else None
        
        # 统计各类事件
        event_counts = {}
        for event in events:
            event_type = event.get("type")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # 工具使用统计
        tool_usage = {}
        for event in events:
            if event.get("type") == "tool_call":
                tool = event.get("tool")
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        # 代码执行统计
        code_executions = event_counts.get("code_execution", 0)
        code_success = len([e for e in events if e.get("type") == "code_result" and e.get("status") == "success"])
        code_errors = len([e for e in events if e.get("type") == "code_result" and e.get("status") == "error"])
        
        # 故障转移统计
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
        搜索包含关键词的 sessions。
        
        Args:
            keyword: 搜索关键词
            user_id: 过滤用户
            limit: 限制返回数量
        
        Returns:
            匹配的 session 列表
        """
        all_sessions = self.list_sessions(user_id=user_id)
        
        matches = []
        for session in all_sessions:
            # 获取对话历史
            conversation = self.get_conversation_history(session["session_id"], session["user_id"])
            
            # 检查是否包含关键词
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
                    ][:3]  # 只返回前 3 条匹配消息
                })
            
            if len(matches) >= limit:
                break
        
        return matches
    
    def _find_log_file(self, session_id: str, user_id: Optional[str] = None) -> Optional[Path]:
        """
        查找 session 的日志文件。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID (None 表示搜索所有用户)
        
        Returns:
            日志文件路径,如果未找到则返回 None
        """
        if user_id:
            log_file = self.log_dir / str(user_id) / f"sess_{session_id}.jsonl"
            if log_file.exists():
                return log_file
            return None
        
        # 搜索所有用户目录
        for user_dir in self.log_dir.iterdir():
            if not user_dir.is_dir():
                continue
            log_file = user_dir / f"sess_{session_id}.jsonl"
            if log_file.exists():
                return log_file
        
        return None

