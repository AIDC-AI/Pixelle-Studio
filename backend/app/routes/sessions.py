"""
Session 路由 - 提供 Session 日志查询 API。
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.utils.session_query import SessionQuery

router = APIRouter(prefix="/sessions", tags=["sessions"])

# 初始化查询器
query = SessionQuery()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_sessions(
    user_id: Optional[str] = Query(None, description="过滤用户 ID"),
    limit: Optional[int] = Query(50, description="限制返回数量", le=500),
    status: Optional[str] = Query(None, description="过滤状态 (success/error/running)")
):
    """
    列出所有 sessions。
    
    - **user_id**: 过滤指定用户 (不提供则返回所有用户)
    - **limit**: 限制返回数量 (默认 50,最大 500)
    - **status**: 过滤状态 (success/error/running)
    """
    try:
        sessions = query.list_sessions(user_id=user_id, limit=limit, status=status)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/events", response_model=List[Dict[str, Any]])
async def get_session_events(
    session_id: str,
    user_id: Optional[str] = Query(None, description="用户 ID"),
    event_type: Optional[str] = Query(None, description="过滤事件类型")
):
    """
    获取 session 的所有事件。
    
    - **session_id**: Session ID
    - **user_id**: 用户 ID (不提供则搜索所有用户)
    - **event_type**: 过滤事件类型 (message/tool_call/code_execution/等)
    """
    try:
        events = query.get_session_events(session_id, user_id, event_type)
        
        if not events:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return events
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/conversation", response_model=List[Dict[str, Any]])
async def get_conversation_history(
    session_id: str,
    user_id: Optional[str] = Query(None, description="用户 ID"),
    include_timestamps: bool = Query(False, description="是否包含时间戳")
):
    """
    获取对话历史 (只包含消息)。
    
    - **session_id**: Session ID
    - **user_id**: 用户 ID
    - **include_timestamps**: 是否包含时间戳和轮次信息
    """
    try:
        conversation = query.get_conversation_history(
            session_id, 
            user_id, 
            include_timestamps
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/tools", response_model=List[Dict[str, Any]])
async def get_tool_calls(
    session_id: str,
    user_id: Optional[str] = Query(None, description="用户 ID"),
    tool_name: Optional[str] = Query(None, description="过滤工具名称")
):
    """
    获取所有工具调用记录。
    
    - **session_id**: Session ID
    - **user_id**: 用户 ID
    - **tool_name**: 过滤指定工具 (load_skill/read_skill_file/等)
    """
    try:
        tool_calls = query.get_tool_calls(session_id, user_id, tool_name)
        return tool_calls
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/code", response_model=List[Dict[str, Any]])
async def get_code_executions(
    session_id: str,
    user_id: Optional[str] = Query(None, description="用户 ID")
):
    """
    获取所有代码执行记录。
    
    - **session_id**: Session ID
    - **user_id**: 用户 ID
    """
    try:
        executions = query.get_code_executions(session_id, user_id)
        return executions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/stats", response_model=Dict[str, Any])
async def get_session_stats(
    session_id: str,
    user_id: Optional[str] = Query(None, description="用户 ID")
):
    """
    获取 session 统计信息。
    
    包括:
    - 总事件数
    - 工具使用统计
    - 代码执行成功率
    - 故障转移次数
    
    - **session_id**: Session ID
    - **user_id**: 用户 ID
    """
    try:
        stats = query.get_session_stats(session_id, user_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/failovers", response_model=List[Dict[str, Any]])
async def get_failovers(
    session_id: str,
    user_id: Optional[str] = Query(None, description="用户 ID")
):
    """
    获取所有故障转移事件。
    
    包括:
    - 认证配置转移
    - 模型转移
    - Thinking Level 降级
    
    - **session_id**: Session ID
    - **user_id**: 用户 ID
    """
    try:
        failovers = query.get_failovers(session_id, user_id)
        return failovers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/", response_model=List[Dict[str, Any]])
async def search_sessions(
    keyword: str = Query(..., description="搜索关键词"),
    user_id: Optional[str] = Query(None, description="过滤用户 ID"),
    limit: int = Query(10, description="限制返回数量", le=100)
):
    """
    搜索包含关键词的 sessions。
    
    在对话历史中搜索关键词。
    
    - **keyword**: 搜索关键词
    - **user_id**: 过滤用户 ID
    - **limit**: 限制返回数量 (默认 10,最大 100)
    """
    try:
        results = query.search_sessions(keyword, user_id, limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

