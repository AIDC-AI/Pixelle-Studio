"""
简化版Session日志记录器
记录对话session的所有事件到JSONL格式文件
"""
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, Optional


class SessionLogger:
    """会话日志记录器"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        """
        初始化会话日志记录器
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（可选）
        """
        self.session_id = session_id
        self.user_id = user_id or "default"
        
        # 创建日志目录
        log_dir = Path(__file__).parent.parent.parent / "logs" / "sessions" / self.user_id
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径
        self.log_file = log_dir / f"sess_{session_id}.jsonl"
        
        # 打开文件句柄（追加模式）
        self.file_handle = open(self.log_file, "a", encoding="utf-8")
    
    def _write_event(self, event_type: str, data: Dict[str, Any], turn: Optional[int] = None):
        """
        写入事件到日志文件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            turn: 回合编号（可选）
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
        self.file_handle.flush()  # 立即写入磁盘
    
    def log_session_start(self, model: str, mcp_server_url: Optional[str] = None):
        """记录会话开始"""
        self._write_event("session_start", {
            "model": model,
            "mcp_server_url": mcp_server_url
        })
    
    def log_session_end(self, status: str, total_turns: int):
        """记录会话结束"""
        self._write_event("session_end", {
            "status": status,
            "total_turns": total_turns
        })
    
    def log_message(self, role: str, content: str, turn: Optional[int] = None):
        """记录消息"""
        self._write_event("message", {
            "role": role,
            "content": content
        }, turn=turn)
    
    def log_status(self, status: str, turn: Optional[int] = None):
        """记录状态"""
        self._write_event("status", {
            "status": status
        }, turn=turn)
    
    def log_tool_call(self, tool: str, args: Dict[str, Any], call_id: str, turn: Optional[int] = None):
        """记录工具调用"""
        self._write_event("tool_call", {
            "tool": tool,
            "args": args,
            "call_id": call_id
        }, turn=turn)
    
    def log_tool_result(self, tool: str, call_id: str, status: str, result: str, duration_ms: float, turn: Optional[int] = None):
        """记录工具结果"""
        self._write_event("tool_result", {
            "tool": tool,
            "call_id": call_id,
            "status": status,
            "result": result[:500],  # 只记录前500字符
            "duration_ms": duration_ms
        }, turn=turn)
    
    def log_code_execution(self, code: str, turn: Optional[int] = None):
        """记录代码执行"""
        self._write_event("code_execution", {
            "code": code
        }, turn=turn)
    
    def log_code_result(self, status: str, stdout: str, stderr: str, output_files: list, duration_ms: float):
        """记录代码执行结果"""
        self._write_event("code_result", {
            "status": status,
            "stdout": stdout[:500],  # 只记录前500字符
            "stderr": stderr[:500],
            "output_files": output_files,
            "duration_ms": duration_ms
        })
    
    def log_context_compaction(self, messages_before: int, messages_after: int):
        """记录上下文压缩"""
        self._write_event("context_compaction", {
            "messages_before": messages_before,
            "messages_after": messages_after
        })
    
    def log_error(self, error: str, error_type: str = "Unknown", turn: Optional[int] = None):
        """记录错误"""
        self._write_event("error", {
            "error": error,
            "error_type": error_type
        }, turn=turn)
    
    def close(self):
        """关闭日志文件"""
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
    
    def __del__(self):
        """析构函数，确保文件被关闭"""
        self.close()

