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

"""Script advisor for generating revision suggestions."""

from typing import Optional, List
from openai import AsyncOpenAI

from app.context.models import (
    ErrorInfo,
    EvaluationResult,
    RevisionAdvice,
    ExecutionContext
)


class ScriptAdvisor:
    """Generates revision advice and prompts for script improvement."""
    
    # Error type to revision type mapping
    ERROR_FIX_MAP = {
        "syntax_error": "fix_syntax",
        "import_error": "fix_import",
        "tool_error": "fix_tool_call",
        "type_error": "fix_type",
        "value_error": "fix_value",
        "runtime_error": "fix_runtime"
    }
    
    def __init__(self, llm_client: Optional[AsyncOpenAI] = None):
        """Initialize the script advisor."""
        self.llm_client = llm_client
        
        if self.llm_client is None:
            self.llm_client = AsyncOpenAI()
    
    async def generate_revision_advice(
        self,
        user_message: str,
        script_content: str,
        error_info: Optional[ErrorInfo],
        evaluation: Optional[EvaluationResult],
        context: ExecutionContext
    ) -> RevisionAdvice:
        """
        Generate revision advice for script improvement.
        
        Args:
            user_message: Original user request
            script_content: Current script content
            error_info: Error information (if execution failed)
            evaluation: Evaluation result (if execution succeeded but validation failed)
            context: Full execution context
            
        Returns:
            RevisionAdvice with suggestions and LLM prompt
        """
        # Determine if revision is needed
        if error_info is None and (evaluation is None or evaluation.meets_requirement):
            return RevisionAdvice(
                should_revise=False,
                revision_type="none",
                specific_suggestions=[],
                llm_prompt=""
            )
        
        # Determine revision type
        if error_info:
            revision_type = self.ERROR_FIX_MAP.get(error_info.error_type, "fix_error")
        elif evaluation and not evaluation.meets_requirement:
            revision_type = "improve_logic"
        else:
            revision_type = "fix_error"
        
        # Generate specific suggestions
        suggestions = self._generate_suggestions(error_info, evaluation)
        
        # Build LLM prompt for revision
        llm_prompt = self._build_revision_prompt(
            user_message=user_message,
            script_content=script_content,
            error_info=error_info,
            evaluation=evaluation,
            context=context
        )
        
        return RevisionAdvice(
            should_revise=True,
            revision_type=revision_type,
            specific_suggestions=suggestions,
            llm_prompt=llm_prompt
        )
    
    def _generate_suggestions(
        self,
        error_info: Optional[ErrorInfo],
        evaluation: Optional[EvaluationResult]
    ) -> List[str]:
        """Generate specific suggestions based on error or evaluation."""
        suggestions = []
        
        if error_info:
            # Error-specific suggestions
            if error_info.error_type == "syntax_error":
                suggestions.append("Fix syntax error in the script")
                suggestions.append("Check for missing colons, parentheses, or indentation")
            
            elif error_info.error_type == "import_error":
                suggestions.append("Remove or replace unavailable imports")
                suggestions.append("Use only available tools via call_tool()")
            
            elif error_info.error_type == "tool_error":
                suggestions.append("Check tool parameter names and types")
                suggestions.append("Verify tool arguments match the tool schema")
            
            elif error_info.error_type in ["type_error", "value_error"]:
                suggestions.append("Check variable types and data structures")
                suggestions.append("Add proper null/error handling")
            
            else:
                suggestions.append("Review the error message and traceback")
                suggestions.append("Add error handling for edge cases")
        
        if evaluation and not evaluation.meets_requirement:
            # Validation-specific suggestions
            suggestions.append(f"Address missing aspects: {', '.join(evaluation.missing_aspects)}")
            suggestions.append("Ensure all user requirements are fulfilled")
            suggestions.append("Verify tool outputs are being used correctly")
        
        return suggestions
    
    def _build_revision_prompt(
        self,
        user_message: str,
        script_content: str,
        error_info: Optional[ErrorInfo],
        evaluation: Optional[EvaluationResult],
        context: ExecutionContext
    ) -> str:
        """Build the prompt for LLM to revise the script."""
        
        prompt_parts = [
            f"User Request: {user_message}",
            "",
            f"Current Script (Iteration {context.current_iteration}):",
            "```python",
            script_content,
            "```",
            ""
        ]
        
        # Add error information
        if error_info:
            prompt_parts.extend([
                "❌ Execution Error:",
                f"Type: {error_info.error_type}",
                f"Message: {error_info.error_message}",
                ""
            ])
            
            if error_info.error_line:
                prompt_parts.append(f"Error Location: Line {error_info.error_line}")
                prompt_parts.append("")
            
            # Add traceback (truncated)
            if error_info.traceback:
                traceback_lines = error_info.traceback.split("\n")
                if len(traceback_lines) > 10:
                    prompt_parts.extend([
                        "Traceback (last 10 lines):",
                        "```",
                        *traceback_lines[-10:],
                        "```",
                        ""
                    ])
                else:
                    prompt_parts.extend([
                        "Traceback:",
                        "```",
                        error_info.traceback,
                        "```",
                        ""
                    ])
        
        # Add evaluation feedback
        if evaluation and not evaluation.meets_requirement:
            prompt_parts.extend([
                "⚠️ Validation Failed:",
                f"Confidence: {evaluation.confidence_score:.2f}",
                f"Reason: {evaluation.evaluation_reason}",
                ""
            ])
            
            if evaluation.missing_aspects:
                prompt_parts.extend([
                    f"Missing Aspects:",
                    *[f"- {aspect}" for aspect in evaluation.missing_aspects],
                    ""
                ])
        
        # Add historical context
        if len(context.iterations) > 1:
            error_types = set()
            for iteration in context.iterations[:-1]:  # Exclude current
                if iteration.error_info:
                    error_types.add(iteration.error_info.error_type)
            
            if error_types:
                prompt_parts.extend([
                    f"⚠️ Previous Errors (Iteration {context.current_iteration}/{context.max_iterations}):",
                    f"- {', '.join(error_types)}",
                    "- Please avoid making the same mistakes",
                    ""
                ])
        
        # Add instructions
        prompt_parts.extend([
            "Please generate a REVISED Python script that:",
            "1. Fixes all errors mentioned above",
            "2. Meets all user requirements",
            "3. Follows the same structure requirements (async main, call_tool, etc.)",
            "",
            "Return ONLY the Python code, no markdown formatting."
        ])
        
        return "\n".join(prompt_parts)
    
    def _summarize_previous_errors(self, context: ExecutionContext) -> str:
        """Summarize errors from previous iterations."""
        error_types = []
        for iteration in context.iterations[:-1]:  # Exclude current iteration
            if iteration.error_info:
                error_types.append(iteration.error_info.error_type)
        
        if not error_types:
            return "None"
        
        # Count occurrences
        error_counts = {}
        for et in error_types:
            error_counts[et] = error_counts.get(et, 0) + 1
        
        return ", ".join([f"{et}({count}x)" for et, count in error_counts.items()])
