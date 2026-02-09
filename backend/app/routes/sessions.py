"""
Session routes - Provides session log query API.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.utils.session_query import SessionQuery

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Initialize query engine
query = SessionQuery()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: Optional[int] = Query(50, description="Limit return count", le=500),
    status: Optional[str] = Query(None, description="Filter by status (success/error/running)")
):
    """
    List all sessions.
    
    - **user_id**: Filter by user (omit to return all users)
    - **limit**: Limit return count (default 50, max 500)
    - **status**: Filter by status (success/error/running)
    """
    try:
        sessions = query.list_sessions(user_id=user_id, limit=limit, status=status)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/events", response_model=List[Dict[str, Any]])
async def get_session_events(
    session_id: str,
    user_id: Optional[str] = Query(None, description="User ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type")
):
    """
    Get all events for a session.
    
    - **session_id**: Session ID
    - **user_id**: User ID (omit to search all users)
    - **event_type**: Filter by event type (message/tool_call/code_execution/etc)
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
    user_id: Optional[str] = Query(None, description="User ID"),
    include_timestamps: bool = Query(False, description="Include timestamps")
):
    """
    Get conversation history (messages only).
    
    - **session_id**: Session ID
    - **user_id**: User ID
    - **include_timestamps**: Include timestamps and turn information
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
    user_id: Optional[str] = Query(None, description="User ID"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name")
):
    """
    Get all tool call records.
    
    - **session_id**: Session ID
    - **user_id**: User ID
    - **tool_name**: Filter by tool name (load_skill/read_skill_file/etc)
    """
    try:
        tool_calls = query.get_tool_calls(session_id, user_id, tool_name)
        return tool_calls
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/code", response_model=List[Dict[str, Any]])
async def get_code_executions(
    session_id: str,
    user_id: Optional[str] = Query(None, description="User ID")
):
    """
    Get all code execution records.
    
    - **session_id**: Session ID
    - **user_id**: User ID
    """
    try:
        executions = query.get_code_executions(session_id, user_id)
        return executions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/stats", response_model=Dict[str, Any])
async def get_session_stats(
    session_id: str,
    user_id: Optional[str] = Query(None, description="User ID")
):
    """
    Get session statistics.
    
    Includes:
    - Total event count
    - Tool usage statistics
    - Code execution success rate
    - Failover count
    
    - **session_id**: Session ID
    - **user_id**: User ID
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
    user_id: Optional[str] = Query(None, description="User ID")
):
    """
    Get all failover events.
    
    Includes:
    - Auth profile failover
    - Model failover
    - Thinking Level downgrade
    
    - **session_id**: Session ID
    - **user_id**: User ID
    """
    try:
        failovers = query.get_failovers(session_id, user_id)
        return failovers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/", response_model=List[Dict[str, Any]])
async def search_sessions(
    keyword: str = Query(..., description="Search keyword"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(10, description="Limit return count", le=100)
):
    """
    Search sessions containing keyword.
    
    Search keyword in conversation history.
    
    - **keyword**: Search keyword
    - **user_id**: Filter by user ID
    - **limit**: Limit return count (default 10, max 100)
    """
    try:
        results = query.search_sessions(keyword, user_id, limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

