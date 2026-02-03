"""
Session Logger - JSONL-based persistent logging for Agent sessions.

每个 session 记录到独立的 .jsonl 文件,包含:
- 所有消息 (user/assistant)
- 所有工具调用和结果
- 所有代码执行和输出
- 故障转移事件
- 上下文压缩事件

目录结构:
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
    """Session 事件类型"""
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
    STATUS = "status"  # Agent 状态更新


class SessionLogger:
    """
    Session 级别的日志记录器。
    
    每个 session 记录到独立的 .jsonl 文件。
    使用缓冲写入提升性能。
    """
    
    def __init__(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        log_dir: Optional[Path] = None,
        buffer_size: int = 10
    ):
        """
        初始化 SessionLogger。
        
        Args:
            session_id: Session ID
            user_id: 用户 ID (None 表示 default)
            log_dir: 日志根目录 (默认: backend/logs/sessions/)
            buffer_size: 缓冲区大小 (达到此大小时写入磁盘)
        """
        self.session_id = session_id
        self.user_id = user_id or "default"
        self.buffer_size = buffer_size
        
        # 创建日志目录
        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / "logs" / "sessions"
        
        self.user_log_dir = log_dir / str(self.user_id)
        self.user_log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径
        self.log_file = self.user_log_dir / f"sess_{session_id}.jsonl"
        
        # 缓冲区
        self.buffer: List[Dict[str, Any]] = []
        
        # 事件计数器
        self.event_count = 0
    
    def _write_event(self, event: Dict[str, Any]):
        """
        写入事件到缓冲区。
        
        Args:
            event: 事件数据
        """
        # 添加时间戳
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # 添加事件序号
        event["seq"] = self.event_count
        self.event_count += 1
        
        # 添加到缓冲区
        self.buffer.append(event)
        
        # 达到缓冲区大小时写入
        if len(self.buffer) >= self.buffer_size:
            self._flush()
    
    def _flush(self):
        """刷新缓冲区到文件"""
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
        记录 session 开始。
        
        Args:
            model: 模型名称
            mcp_server_url: MCP 服务器 URL
            **kwargs: 其他元数据
        """
        self._write_event({
            "type": EventType.SESSION_START,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model": model,
            "mcp_server_url": mcp_server_url,
            **kwargs
        })
        self._flush()  # 立即写入
    
    def log_message(
        self, 
        role: str, 
        content: str,
        turn: Optional[int] = None,
        **kwargs
    ):
        """
        记录消息 (user/assistant)。
        
        Args:
            role: 角色 ("user" 或 "assistant")
            content: 消息内容
            turn: 对话轮次
            **kwargs: 其他元数据
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
        记录工具调用。
        
        Args:
            tool: 工具名称
            args: 工具参数
            call_id: 调用 ID
            turn: 对话轮次
            **kwargs: 其他元数据
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
        记录工具结果。
        
        Args:
            tool: 工具名称
            call_id: 调用 ID
            status: 状态 ("success" 或 "error")
            result: 结果数据
            duration_ms: 执行时间 (毫秒)
            **kwargs: 其他元数据
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
        记录代码执行。
        
        Args:
            code: 代码内容
            turn: 对话轮次
            **kwargs: 其他元数据
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
        记录代码执行结果。
        
        Args:
            status: 状态 ("success" 或 "error")
            stdout: 标准输出
            stderr: 标准错误
            output_files: 生成的文件列表
            duration_ms: 执行时间 (毫秒)
            **kwargs: 其他元数据
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
        记录错误。
        
        Args:
            error: 错误消息
            error_type: 错误类型
            turn: 对话轮次
            **kwargs: 其他元数据
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
        记录上下文压缩。
        
        Args:
            messages_before: 压缩前消息数
            messages_after: 压缩后消息数
            strategy: 压缩策略
            **kwargs: 其他元数据
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
        记录故障转移。
        
        Args:
            layer: 转移层级 ("auth", "model", "thinking")
            from_value: 原始值
            to_value: 目标值
            reason: 转移原因
            **kwargs: 其他元数据
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
        记录状态更新。
        
        Args:
            content: 状态消息
            turn: 对话轮次
            **kwargs: 其他元数据
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
        记录 session 结束。
        
        Args:
            status: 结束状态 ("success", "error", "cancelled")
            total_turns: 总对话轮次
            total_events: 总事件数
            **kwargs: 其他元数据
        """
        self._write_event({
            "type": EventType.SESSION_END,
            "status": status,
            "total_turns": total_turns,
            "total_events": total_events or self.event_count,
            **kwargs
        })
        self._flush()  # 立即写入
    
    def close(self):
        """关闭 logger,刷新缓冲区"""
        self._flush()
    
    def __enter__(self):
        """Context manager 支持"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 支持"""
        self.close()
        return False

