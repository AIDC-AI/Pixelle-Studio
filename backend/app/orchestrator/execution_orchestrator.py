"""Execution orchestrator for managing the generate-execute-evaluate-revise loop."""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import WebSocket

from app.context.models import ExecutionContext, IterationRecord, ErrorInfo
from app.context.context_manager import ContextManager
from app.evaluation.error_evaluator import RuntimeErrorEvaluator
from app.evaluation.result_validator import ResultValidator
from app.evaluation.script_advisor import ScriptAdvisor
from app.execution.runner import run_script


@dataclass
class ExecutionConfig:
    """Configuration for execution orchestration."""
    max_iterations: int = 3
    script_execution_timeout: int = 60
    llm_generation_timeout: int = 30
    enable_error_evaluation: bool = True
    enable_result_validation: bool = True
    validation_confidence_threshold: float = 0.7


class ExecutionOrchestrator:
    """Orchestrates the execution loop with self-evaluation."""
    
    def __init__(
        self,
        context_manager: ContextManager,
        config: Optional[ExecutionConfig] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            context_manager: Context manager for storing execution history
            config: Configuration for orchestration
        """
        self.context_manager = context_manager
        self.config = config or ExecutionConfig()
        
        # Initialize evaluators
        self.error_evaluator = RuntimeErrorEvaluator()
        self.result_validator = ResultValidator()
        self.script_advisor = ScriptAdvisor()
        
        # Track WebSocket connection state
        self._ws_disconnected = False
    
    async def execute_with_self_evaluation(
        self,
        websocket: WebSocket,
        chat_id: str,
        user_message: str,
        selected_tools: List[Dict[str, Any]]
    ) -> ExecutionContext:
        """
        Execute workflow with self-evaluation loop.
        
        Workflow:
        1. Generate script (using context summary)
        2. Execute script
        3. Evaluate execution (error + result validation)
        4. If success and valid -> done
        5. If failed or invalid and iterations remain -> advise revision and loop
        
        Args:
            websocket: WebSocket for streaming updates
            chat_id: Chat session ID
            user_message: User's request
            selected_tools: Tools selected for this request
            
        Returns:
            ExecutionContext with all iterations
        """
        # Reset disconnection flag for new execution
        self._ws_disconnected = False
        
        # Initialize context
        ctx = await self.context_manager.initialize_context(
            chat_id=chat_id,
            user_message=user_message,
            selected_tools=selected_tools,
            max_iterations=self.config.max_iterations
        )
        
        if not await self._send_status(websocket, "Starting workflow execution with self-evaluation..."):
            # Client disconnected immediately
            return ctx
        
        # Evaluation loop
        while ctx.current_iteration < ctx.max_iterations and not self._ws_disconnected:
            ctx.current_iteration += 1
            
            if not await self._send_iteration_start(websocket, ctx.current_iteration, ctx.max_iterations):
                break
            
            # === Phase 1: Generate/Revise Script ===
            if not await self._send_status(
                websocket,
                f"[Iteration {ctx.current_iteration}/{ctx.max_iterations}] Generating script..."
            ):
                break
            
            script_content = await self._generate_or_revise_script(ctx)
            
            # Save script to file
            script_path = await self._save_script(chat_id, ctx.current_iteration, script_content)
            
            # Send script to frontend
            if not await self._safe_send(websocket, {
                "type": "script",
                "iteration": ctx.current_iteration,
                "content": script_content
            }):
                break
            
            # === Phase 2: Execute Script ===
            if not await self._send_status(
                websocket,
                f"[Iteration {ctx.current_iteration}/{ctx.max_iterations}] Executing workflow..."
            ):
                break
            
            execution_logs, execution_result, execution_status = await self._execute_script(
                websocket,
                script_path
            )
            
            # === Phase 3: Evaluate Execution ===
            if not await self._send_status(
                websocket,
                f"[Iteration {ctx.current_iteration}/{ctx.max_iterations}] Evaluating results..."
            ):
                break
            
            # 3a. Evaluate errors (if any)
            error_info = None
            if self.config.enable_error_evaluation and execution_status != "success":
                error_info = await self.error_evaluator.evaluate_error(
                    execution_logs=execution_logs,
                    script_content=script_content
                )
            
            # 3b. Validate results (if execution succeeded)
            evaluation = None
            if self.config.enable_result_validation and execution_status == "success":
                evaluation = await self.result_validator.validate_result(
                    user_message=user_message,
                    execution_result=execution_result or {},
                    execution_logs=execution_logs,
                    context=ctx
                )
                
                # Send evaluation to frontend
                if not await self._safe_send(websocket, {
                    "type": "evaluation_result",
                    "iteration": ctx.current_iteration,
                    "meets_requirement": evaluation.meets_requirement,
                    "confidence_score": evaluation.confidence_score,
                    "reason": evaluation.evaluation_reason
                }):
                    break
            
            # === Phase 4: Record Iteration ===
            iteration_record = IterationRecord(
                iteration_id=ctx.current_iteration,
                timestamp=datetime.now(),
                script_content=script_content,
                script_path=script_path,
                execution_status=execution_status,
                execution_logs=execution_logs,
                execution_result=execution_result,
                error_info=error_info,
                evaluation=evaluation
            )
            
            await self.context_manager.store_iteration(chat_id, iteration_record)
            ctx.iterations.append(iteration_record)
            
            # === Phase 5: Decision ===
            # Success condition: no errors AND (no validation OR validation passed)
            is_success = (
                execution_status == "success" and
                error_info is None and
                (evaluation is None or evaluation.meets_requirement)
            )
            
            if is_success:
                ctx.status = "success"
                await self.context_manager.update_context_status(chat_id, "success", ctx.current_iteration)
                await self._send_iteration_end(websocket, ctx.current_iteration, "success")
                await self._send_status(websocket, "✅ Execution successful and meets requirements!")
                break
            
            # Check if max iterations reached
            if ctx.current_iteration >= ctx.max_iterations:
                ctx.status = "failed"
                await self.context_manager.update_context_status(chat_id, "failed", ctx.current_iteration)
                await self._send_iteration_end(websocket, ctx.current_iteration, "failed")
                await self._send_status(websocket, "❌ Max iterations reached without success")
                break
            
            # === Phase 6: Generate Revision Advice ===
            if not await self._send_status(
                websocket,
                f"[Iteration {ctx.current_iteration}/{ctx.max_iterations}] Generating revision advice..."
            ):
                break
            
            revision_advice = await self.script_advisor.generate_revision_advice(
                user_message=user_message,
                script_content=script_content,
                error_info=error_info,
                evaluation=evaluation,
                context=ctx
            )
            
            # Update iteration record with advice
            iteration_record.revision_advice = revision_advice
            await self.context_manager.store_iteration(chat_id, iteration_record)
            
            # Send advice to frontend
            if not await self._safe_send(websocket, {
                "type": "revision_advice",
                "iteration": ctx.current_iteration,
                "advice": revision_advice.to_dict()
            }):
                break
            
            if not await self._send_iteration_end(websocket, ctx.current_iteration, "needs_revision"):
                break
            
            # Continue to next iteration
        
        return ctx
    
    async def _generate_or_revise_script(self, ctx: ExecutionContext) -> str:
        """Generate or revise script based on context."""
        from app.llm_adapter import generate_or_revise_script
        
        # Build context summary
        context_summary = self.context_manager.build_context_summary(ctx)
        
        # Get previous iteration (if any)
        previous_iteration = ctx.get_latest_iteration()
        
        # Generate script
        script_content = await generate_or_revise_script(
            user_message=ctx.user_message,
            tools=ctx.selected_tools,
            context_summary=context_summary,
            previous_iteration=previous_iteration
        )
        
        return script_content
    
    async def _save_script(self, chat_id: str, iteration: int, script_content: str) -> str:
        """Save script to file and return path."""
        # Use scripts directory outside backend
        script_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../scripts")
        )
        os.makedirs(script_dir, exist_ok=True)
        
        # Unique filename  with iteration number
        filename = f"{chat_id}_iter{iteration:02d}_{uuid.uuid4().hex[:8]}.py"
        script_path = os.path.join(script_dir, filename)
        
        with open(script_path, "w") as f:
            f.write(script_content)
        
        return script_path
    
    async def _execute_script(
        self,
        websocket: WebSocket,
        script_path: str
    ) -> tuple[List[Dict], Optional[Dict], str]:
        """
        Execute script and collect logs.
        
        Returns:
            (execution_logs, execution_result, execution_status)
        """
        execution_logs = []
        execution_result = None
        execution_status = "success"
        
        try:
            # Run script and stream logs
            async for log in run_script(script_path, cwd=os.path.dirname(script_path)):
                execution_logs.append(log)
                
                # Forward logs to websocket (check disconnection)
                if not await self._safe_send(websocket, log):
                    # Client disconnected, stop streaming logs
                    break
                
                # Capture result
                if log.get("type") == "result":
                    if log.get("status") == "success":
                        execution_status = "success"
                    else:
                        execution_status = "runtime_error"
                    
                    # Try to extract actual result from logs
                    # Look for JSON output in stdout
                    for prev_log in reversed(execution_logs):
                        if prev_log.get("stream") == "stdout":
                            content = prev_log.get("content", "")
                            if content.strip().startswith("{"):
                                try:
                                    import json
                                    execution_result = json.loads(content)
                                    break
                                except:
                                    pass
        
        except Exception as e:
            execution_status = "runtime_error"
            execution_logs.append({
                "type": "error",
                "content": f"Execution failed: {str(e)}"
            })
        
        return execution_logs, execution_result, execution_status
    
    async def _safe_send(self, websocket: WebSocket, data: dict) -> bool:
        """
        Safely send JSON to websocket, catching disconnections.
        
        Returns:
            True if sent successfully, False if disconnected
        """
        if self._ws_disconnected:
            return False
        
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            # Mark as disconnected and stop further sends
            self._ws_disconnected = True
            print(f"[Orchestrator] WebSocket disconnected during send: {e}")
            return False
    
    async def _send_status(self, websocket: WebSocket, message: str) -> bool:
        """Send status update to websocket."""
        return await self._safe_send(websocket, {
            "type": "status",
            "content": message
        })
    
    async def _send_iteration_start(self, websocket: WebSocket, iteration: int, max_iterations: int) -> bool:
        """Send iteration start message."""
        return await self._safe_send(websocket, {
            "type": "iteration_start",
            "iteration": iteration,
            "max_iterations": max_iterations
        })
    
    async def _send_iteration_end(self, websocket: WebSocket, iteration: int, status: str) -> bool:
        """Send iteration end message."""
        return await self._safe_send(websocket, {
            "type": "iteration_end",
            "iteration": iteration,
            "status": status  # success, failed, needs_revision
        })
