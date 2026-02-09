"""
SubAgent API Routes
Provides API endpoints for querying and managing SubAgents
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.subagent import get_subagent_manager

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subagents", tags=["SubAgents"])


# ===== Request/Response Models =====

class SubAgentInfo(BaseModel):
    """SubAgent information"""
    subagent_id: str
    parent_session_id: str
    task: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ===== API Endpoints =====

@router.get("/{subagent_id}", response_model=Dict[str, Any])
async def get_subagent_status(subagent_id: str):
    """
    Get status of a specific SubAgent.
    
    Args:
        subagent_id: SubAgent ID
        
    Returns:
        SubAgent status information
    """
    logger.info(f"[API] Getting status for subagent: {subagent_id}")
    
    manager = get_subagent_manager()
    status_info = manager.get_status(subagent_id)
    
    if not status_info:
        raise HTTPException(status_code=404, detail=f"SubAgent {subagent_id} not found")
    
    return status_info


@router.get("/", response_model=Dict[str, Any])
async def list_subagents(
    parent_session_id: Optional[str] = None,
    status_filter: Optional[str] = None  # "running" or "completed"
):
    """
    List all SubAgents.
    
    Args:
        parent_session_id: Optional, only return SubAgents for a specific parent session
        status_filter: Optional, filter by status ("running" or "completed")
        
    Returns:
        SubAgent list
    """
    logger.info(f"[API] Listing subagents (parent_session={parent_session_id}, status={status_filter})")
    
    manager = get_subagent_manager()
    
    if status_filter == "running":
        subagents = manager.list_running(parent_session_id)
    elif status_filter == "completed":
        subagents = manager.list_completed(parent_session_id)
    else:
        # Return all
        running = manager.list_running(parent_session_id)
        completed = manager.list_completed(parent_session_id)
        subagents = running + completed
    
    return {
        "total": len(subagents),
        "subagents": subagents
    }

