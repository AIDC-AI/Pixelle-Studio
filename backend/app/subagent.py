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
Sub-Agent Manager
For task parallelization and background execution.
"""
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

import logging
logger = logging.getLogger(__name__)


@dataclass
class SubAgentTask:
    """Sub-Agent task information"""
    subagent_id: str
    parent_session_id: str
    task: str
    status: str  # "pending", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class SubAgentManager:
    """Sub-Agent Manager"""
    
    def __init__(self):
        self.running_subagents: Dict[str, SubAgentTask] = {}
        self.completed_subagents: Dict[str, SubAgentTask] = {}
    
    async def spawn(
        self,
        parent_session_id: str,
        task: str,
        user_id: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_turns: int = 10
    ) -> str:
        """
        Spawn a Sub-Agent to execute a background task.
        
        Args:
            parent_session_id: Parent session ID
            task: Task description to execute
            user_id: User ID
            model: Model to use
            max_turns: Maximum number of turns
            
        Returns:
            subagent_id: Sub-Agent ID
        """
        subagent_id = f"subagent_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"[SubAgentManager] Spawning sub-agent {subagent_id} for task: {task[:50]}...")
        
        # Create task record
        task_info = SubAgentTask(
            subagent_id=subagent_id,
            parent_session_id=parent_session_id,
            task=task,
            status="pending",
            started_at=datetime.now()
        )
        self.running_subagents[subagent_id] = task_info
        
        # Run Sub-Agent in background
        asyncio.create_task(
            self._run_subagent(
                subagent_id=subagent_id,
                task=task,
                user_id=user_id,
                model=model,
                max_turns=max_turns
            )
        )
        
        return subagent_id
    
    async def _run_subagent(
        self,
        subagent_id: str,
        task: str,
        user_id: Optional[str],
        model: str,
        max_turns: int
    ):
        """
        Run Sub-Agent (background execution).
        
        Args:
            subagent_id: Sub-Agent ID
            task: Task description
            user_id: User ID
            model: Model to use
            max_turns: Maximum number of turns
        """
        task_info = self.running_subagents[subagent_id]
        task_info.status = "running"
        
        try:
            logger.info(f"[SubAgent {subagent_id}] Starting execution...")
            
            # Create independent agent instance
            from app.agent import SkillAgent
            
            subagent = SkillAgent(
                user_id=user_id,
                max_turns=max_turns
            )
            # Set model (if different from default)
            if model and model != subagent.model:
                subagent.model = model
            
            # Execute task
            final_result = None
            async for event in subagent.run(
                user_message=task,
                session_id=subagent_id
            ):
                # Only get final result
                if event["type"] == "final_result":
                    final_result = event.get("result", {})
            
            # Update task status
            task_info.status = "completed"
            task_info.completed_at = datetime.now()
            task_info.result = final_result
            
            # Move to completed list
            self.completed_subagents[subagent_id] = task_info
            del self.running_subagents[subagent_id]
            
            logger.info(f"[SubAgent {subagent_id}] Completed successfully")
            
        except Exception as e:
            logger.error(f"[SubAgent {subagent_id}] Failed: {e}", exc_info=True)
            
            # Update task status
            task_info.status = "failed"
            task_info.completed_at = datetime.now()
            task_info.error = str(e)
            
            # Move to completed list
            self.completed_subagents[subagent_id] = task_info
            del self.running_subagents[subagent_id]
    
    def get_status(self, subagent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a Sub-Agent.
        
        Args:
            subagent_id: Sub-Agent ID
            
        Returns:
            Status info dictionary, or None if not found
        """
        # First search running tasks
        if subagent_id in self.running_subagents:
            task = self.running_subagents[subagent_id]
            return {
                "subagent_id": task.subagent_id,
                "parent_session_id": task.parent_session_id,
                "task": task.task,
                "status": task.status,
                "started_at": task.started_at.isoformat(),
                "completed_at": None,
                "result": None,
                "error": None
            }
        
        # Then search completed tasks
        if subagent_id in self.completed_subagents:
            task = self.completed_subagents[subagent_id]
            return {
                "subagent_id": task.subagent_id,
                "parent_session_id": task.parent_session_id,
                "task": task.task,
                "status": task.status,
                "started_at": task.started_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "result": task.result,
                "error": task.error
            }
        
        return None
    
    def list_running(self, parent_session_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """
        List all running Sub-Agents.
        
        Args:
            parent_session_id: Optional, only return Sub-Agents for a specific parent session
            
        Returns:
            List of Sub-Agent info
        """
        tasks = self.running_subagents.values()
        
        if parent_session_id:
            tasks = [t for t in tasks if t.parent_session_id == parent_session_id]
        
        return [
            {
                "subagent_id": t.subagent_id,
                "parent_session_id": t.parent_session_id,
                "task": t.task[:100],  # Only return first 100 chars
                "status": t.status,
                "started_at": t.started_at.isoformat()
            }
            for t in tasks
        ]
    
    def list_completed(self, parent_session_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """
        List all completed Sub-Agents.
        
        Args:
            parent_session_id: Optional, only return Sub-Agents for a specific parent session
            
        Returns:
            List of Sub-Agent info
        """
        tasks = self.completed_subagents.values()
        
        if parent_session_id:
            tasks = [t for t in tasks if t.parent_session_id == parent_session_id]
        
        return [
            {
                "subagent_id": t.subagent_id,
                "parent_session_id": t.parent_session_id,
                "task": t.task[:100],
                "status": t.status,
                "started_at": t.started_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "error": t.error
            }
            for t in tasks
        ]


# Global SubAgent Manager instance
_subagent_manager = SubAgentManager()


def get_subagent_manager() -> SubAgentManager:
    """Get global SubAgent Manager instance"""
    return _subagent_manager

