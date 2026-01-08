"""Execution orchestrator for managing the generate-execute-evaluate-revise loop."""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import WebSocket
import aiohttp
from pathlib import Path

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
        selected_tools: List[Dict[str, Any]],
        file_urls: List[str] = None,
        suggested_skill: str = None
    ) -> ExecutionContext:
        """
        Execute workflow with self-evaluation loop.
        
        Workflow:
        1. Generate script (using skill guidance and context summary)
        2. Execute script
        3. Evaluate execution (error + result validation)
        4. If success and valid -> done
        5. If failed or invalid and iterations remain -> advise revision and loop
        
        Args:
            websocket: WebSocket for streaming updates
            chat_id: Chat session ID
            user_message: User's request
            selected_tools: MCP tools selected for this request (optional)
            file_urls: File URLs uploaded by user
            suggested_skill: Skill name to use (optional, will auto-detect if not provided)
            
        Returns:
            ExecutionContext with all iterations
        """
        # Store suggested_skill in context for use in script generation
        self._current_suggested_skill = suggested_skill
        # Reset disconnection flag for new execution
        self._ws_disconnected = False
        
        # Initialize context
        ctx = await self.context_manager.initialize_context(
            chat_id=chat_id,
            user_message=user_message,
            selected_tools=selected_tools,
            max_iterations=self.config.max_iterations,
            file_urls=file_urls or []
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
            
            script_content = await self._generate_or_revise_script(ctx, self._current_suggested_skill)
            
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
    
    async def _get_files_summary(self, file_urls: List[str]) -> Dict[str, Any]:
        """
        Get summary information for uploaded files.
        
        For Excel files: Get headers and first 3 rows to understand structure
        For images: Use vision API to understand image content
        
        Args:
            file_urls: List of file URLs
            
        Returns:
            Dictionary mapping file URLs to their summary information
        """
        if not file_urls:
            return {}
        
        file_summaries = {}
        
        for file_url in file_urls:
            try:
                # Determine file type from URL or extension
                file_path = Path(file_url)
                file_ext = file_path.suffix.lower()
                
                if file_ext in ['.xlsx', '.xls', '.csv']:
                    # Handle Excel/CSV files
                    summary = await self._summarize_excel_file(file_url, file_ext)
                    file_summaries[file_url] = summary
                    
                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    # Handle image files
                    summary = await self._summarize_image_file(file_url)
                    file_summaries[file_url] = summary
                    
                else:
                    # Unknown file type
                    file_summaries[file_url] = {
                        "type": "unknown",
                        "filename": file_path.name,
                        "note": "File type not supported for automatic summarization"
                    }
                    
            except Exception as e:
                file_summaries[file_url] = {
                    "type": "error",
                    "error": str(e),
                    "note": f"Failed to summarize file: {str(e)}"
                }
        
        return file_summaries
    
    async def _summarize_excel_file(self, file_url: str, file_ext: str) -> Dict[str, Any]:
        """
        Summarize Excel/CSV file by extracting headers and first 3 rows.
        
        Args:
            file_url: File URL (can be local path or remote URL)
            file_ext: File extension
            
        Returns:
            Dictionary with file structure information
        """
        try:
            import pandas as pd
            
            # Check if it's a remote URL or local path
            if file_url.startswith(('http://', 'https://')):
                # Remote file - download first
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_url) as response:
                        content = await response.read()
                        
                        # Save to temporary file
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_file.write(content)
                            tmp_path = tmp_file.name
                        
                        # Read with pandas
                        if file_ext == '.csv':
                            df = pd.read_csv(tmp_path)
                        else:
                            df = pd.read_excel(tmp_path)
                        
                        # Clean up temp file
                        os.remove(tmp_path)
            else:
                # Local file
                if file_ext == '.csv':
                    df = pd.read_csv(file_url)
                else:
                    df = pd.read_excel(file_url)
            
            # Extract summary information
            summary = {
                "type": "excel" if file_ext in ['.xlsx', '.xls'] else "csv",
                "filename": Path(file_url).name,
                "shape": {
                    "rows": len(df),
                    "columns": len(df.columns)
                },
                "columns": df.columns.tolist(),
                "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "preview_rows": df.head(3).to_dict(orient='records'),
                "sample_data": df.head(3).to_string()
            }
            
            return summary
            
        except Exception as e:
            return {
                "type": "excel_error",
                "error": str(e),
                "note": f"Failed to read Excel/CSV file: {str(e)}"
            }
    
    async def _summarize_image_file(self, file_url: str) -> Dict[str, Any]:
        """
        Summarize image file using vision API.
        
        Args:
            file_url: Image file URL (can be local path or remote URL)
            
        Returns:
            Dictionary with image content description
        """
        try:
            from openai import AsyncOpenAI
            
            # Use the same LLM configuration
            client = AsyncOpenAI(
                api_key="REDACTED_API_KEY",
                base_url="https://REDACTED_BASE_URL_HOST/v1"
            )
            
            # If it's a local file, we need to convert to base64 or upload
            # For simplicity, we'll assume the URL is accessible
            image_url_for_api = file_url
            
            # If it's a local file path, convert to base64
            if not file_url.startswith(('http://', 'https://')):
                import base64
                with open(file_url, 'rb') as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    # Detect image format
                    file_ext = Path(file_url).suffix.lower()
                    mime_type = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.bmp': 'image/bmp',
                        '.webp': 'image/webp'
                    }.get(file_ext, 'image/jpeg')
                    
                    image_url_for_api = f"data:{mime_type};base64,{image_data}"
            
            # Call vision API
            response = await client.chat.completions.create(
                model="gpt-4o",  # Use a vision-capable model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请简要描述这张图片的内容，包括主要物体、场景、颜色、构图等关键信息。用中文回答，控制在200字以内。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url_for_api
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            description = response.choices[0].message.content
            
            return {
                "type": "image",
                "filename": Path(file_url).name,
                "description": description,
                "note": "Image content analyzed by vision API"
            }
            
        except Exception as e:
            return {
                "type": "image_error",
                "error": str(e),
                "note": f"Failed to analyze image: {str(e)}"
            }
    
    async def _generate_or_revise_script(self, ctx: ExecutionContext, suggested_skill: str = None) -> str:
        """Generate or revise script based on context and skill guidance."""
        from app.llm_adapter import generate_script_with_skill
        
        # Get file summaries if files are present
        file_summaries = None
        if ctx.file_urls:
            file_summaries = await self._get_files_summary(ctx.file_urls)
            print(f"[Orchestrator] Generated file summaries for {len(file_summaries)} files")
        
        # Build context summary
        context_summary = self.context_manager.build_context_summary(ctx)
        
        # Append file summaries to context if available
        if file_summaries:
            context_summary += "\n\n=== File Summaries ===\n"
            for file_url, summary in file_summaries.items():
                context_summary += f"\nFile: {summary.get('filename', file_url)}\n"
                context_summary += f"Type: {summary.get('type', 'unknown')}\n"
                
                if summary.get('type') in ['excel', 'csv']:
                    context_summary += f"Shape: {summary.get('shape', {}).get('rows', '?')} rows × {summary.get('shape', {}).get('columns', '?')} columns\n"
                    context_summary += f"Columns: {', '.join(summary.get('columns', []))}\n"
                    context_summary += f"Preview (first 3 rows):\n{summary.get('sample_data', 'N/A')}\n"
                elif summary.get('type') == 'image':
                    context_summary += f"Description: {summary.get('description', 'N/A')}\n"
                elif summary.get('error'):
                    context_summary += f"Error: {summary.get('error', 'Unknown error')}\n"
                
                context_summary += "\n"
        
        # Detect skill from file types if not provided
        if not suggested_skill and ctx.file_urls:
            for url in ctx.file_urls:
                if any(url.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.csv']):
                    suggested_skill = 'xlsx'
                    print(f"[Orchestrator] Auto-detected skill: {suggested_skill}")
                    break
        
        # Get previous iteration (if any)
        previous_iteration = ctx.get_latest_iteration()
        
        # Generate script using skill-based approach
        script_content = await generate_script_with_skill(
            user_message=ctx.user_message,
            skill_name=suggested_skill,
            file_urls=ctx.file_urls,
            context_summary=context_summary,
            previous_iteration=previous_iteration,
            mcp_tools=ctx.selected_tools if ctx.selected_tools else None
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
