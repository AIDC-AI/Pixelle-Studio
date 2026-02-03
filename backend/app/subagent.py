"""
Sub-Agent 管理器
用于实现任务并行化和后台执行
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
    """Sub-Agent 任务信息"""
    subagent_id: str
    parent_session_id: str
    task: str
    status: str  # "pending", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class SubAgentManager:
    """Sub-Agent 管理器"""
    
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
        生成一个 Sub-Agent 来执行后台任务
        
        Args:
            parent_session_id: 父会话 ID
            task: 要执行的任务描述
            user_id: 用户 ID
            model: 使用的模型
            max_turns: 最大轮次
            
        Returns:
            subagent_id: Sub-Agent ID
        """
        subagent_id = f"subagent_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"[SubAgentManager] Spawning sub-agent {subagent_id} for task: {task[:50]}...")
        
        # 创建任务记录
        task_info = SubAgentTask(
            subagent_id=subagent_id,
            parent_session_id=parent_session_id,
            task=task,
            status="pending",
            started_at=datetime.now()
        )
        self.running_subagents[subagent_id] = task_info
        
        # 后台运行 Sub-Agent
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
        运行 Sub-Agent (后台执行)
        
        Args:
            subagent_id: Sub-Agent ID
            task: 任务描述
            user_id: 用户 ID
            model: 使用的模型
            max_turns: 最大轮次
        """
        task_info = self.running_subagents[subagent_id]
        task_info.status = "running"
        
        try:
            logger.info(f"[SubAgent {subagent_id}] Starting execution...")
            
            # 创建独立的 Agent 实例
            from app.agent import SkillAgent
            
            subagent = SkillAgent(
                user_id=user_id,
                max_turns=max_turns
            )
            # 设置模型（如果与默认不同）
            if model and model != subagent.model:
                subagent.model = model
            
            # 执行任务
            final_result = None
            async for event in subagent.run(
                user_message=task,
                session_id=subagent_id
            ):
                # 只获取最终结果
                if event["type"] == "final_result":
                    final_result = event.get("result", {})
            
            # 更新任务状态
            task_info.status = "completed"
            task_info.completed_at = datetime.now()
            task_info.result = final_result
            
            # 移动到已完成列表
            self.completed_subagents[subagent_id] = task_info
            del self.running_subagents[subagent_id]
            
            logger.info(f"[SubAgent {subagent_id}] Completed successfully")
            
        except Exception as e:
            logger.error(f"[SubAgent {subagent_id}] Failed: {e}", exc_info=True)
            
            # 更新任务状态
            task_info.status = "failed"
            task_info.completed_at = datetime.now()
            task_info.error = str(e)
            
            # 移动到已完成列表
            self.completed_subagents[subagent_id] = task_info
            del self.running_subagents[subagent_id]
    
    def get_status(self, subagent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 Sub-Agent 的状态
        
        Args:
            subagent_id: Sub-Agent ID
            
        Returns:
            状态信息字典，如果不存在则返回 None
        """
        # 先查找运行中的
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
        
        # 再查找已完成的
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
        列出所有运行中的 Sub-Agent
        
        Args:
            parent_session_id: 可选，只返回特定父会话的 Sub-Agents
            
        Returns:
            Sub-Agent 信息列表
        """
        tasks = self.running_subagents.values()
        
        if parent_session_id:
            tasks = [t for t in tasks if t.parent_session_id == parent_session_id]
        
        return [
            {
                "subagent_id": t.subagent_id,
                "parent_session_id": t.parent_session_id,
                "task": t.task[:100],  # 只返回前100字符
                "status": t.status,
                "started_at": t.started_at.isoformat()
            }
            for t in tasks
        ]
    
    def list_completed(self, parent_session_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """
        列出所有已完成的 Sub-Agent
        
        Args:
            parent_session_id: 可选，只返回特定父会话的 Sub-Agents
            
        Returns:
            Sub-Agent 信息列表
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


# 全局 SubAgent Manager 实例
_subagent_manager = SubAgentManager()


def get_subagent_manager() -> SubAgentManager:
    """获取全局 SubAgent Manager 实例"""
    return _subagent_manager

