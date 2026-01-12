"""Result validator using LLM to evaluate execution results."""

import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from app.context.models import EvaluationResult, ExecutionContext


class ResultValidator:
    """Validates execution results against user requirements using LLM."""
    
    def __init__(self, llm_client: Optional[AsyncOpenAI] = None, llm_model: str = None):
        """
        Initialize the result validator.
        
        Args:
            llm_client: OpenAI client instance (if None, will create from env)
            llm_model: LLM model name (if None, will use from config)
        """
        self.llm_client = llm_client
        self.llm_model = llm_model
        
        if self.llm_client is None:
            self.llm_client = AsyncOpenAI()
        
        if self.llm_model is None:
            from app.llm_adapter import DEFAULT_MODEL
            self.llm_model = DEFAULT_MODEL
    
    async def validate_result(
        self,
        user_message: str,
        execution_result: Dict[str, Any],
        execution_logs: List[Dict],
        context: ExecutionContext
    ) -> EvaluationResult:
        """
        Evaluate whether execution result meets user requirements.
        
        Args:
            user_message: Original user request
            execution_result: Final execution result from script
            execution_logs: All execution logs
            context: Full execution context
            
        Returns:
            EvaluationResult with assessment
        """
        # Build evaluation prompt
        evaluation_prompt = self._build_evaluation_prompt(
            user_message=user_message,
            execution_result=execution_result,
            execution_logs=execution_logs
        )
        
        system_prompt = """You are an expert evaluator for workflow execution results.

Your task is to determine whether the execution result satisfies the user's request.

Consider:
1. **Completeness**: Does the result include all requested operations?
2. **Correctness**: Are the returned values reasonable and correct?
3. **Usability**: Is the result actually usable (not mock/placeholder data)?

Output MUST be valid JSON with this exact structure:
{
    "meets_requirement": true or false,
    "confidence_score": 0.0 to 1.0,
    "evaluation_reason": "Detailed explanation of your assessment",
    "missing_aspects": ["aspect1", "aspect2"] or []
}

Be strict: if anything is missing or seems wrong, set meets_requirement to false."""
        
        try:
            # Call LLM for evaluation
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": evaluation_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3  # Lower temperature for more consistent evaluation
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            return EvaluationResult(
                meets_requirement=result_json.get("meets_requirement", False),
                confidence_score=result_json.get("confidence_score", 0.0),
                evaluation_reason=result_json.get("evaluation_reason", ""),
                missing_aspects=result_json.get("missing_aspects", [])
            )
            
        except Exception as e:
            # Fallback: if LLM fails, assume validation failed
            print(f"[ResultValidator] LLM evaluation failed: {e}")
            return EvaluationResult(
                meets_requirement=False,
                confidence_score=0.0,
                evaluation_reason=f"Evaluation failed due to error: {str(e)}",
                missing_aspects=["evaluation_error"]
            )
    
    def _build_evaluation_prompt(
        self,
        user_message: str,
        execution_result: Dict[str, Any],
        execution_logs: List[Dict]
    ) -> str:
        """Build the evaluation prompt for LLM."""
        # Extract last N log lines (stdout only, skip verbose logs)
        relevant_logs = [
            log for log in execution_logs[-30:]  # Last 30 logs
            if log.get("stream") == "stdout" and log.get("content")
        ]
        
        logs_text = "\n".join([
            log["content"] for log in relevant_logs
        ]) if relevant_logs else "(No stdout logs)"
        
        # Format execution result
        result_text = json.dumps(execution_result, indent=2, ensure_ascii=False) if execution_result else "(No result returned)"
        
        prompt = f"""
User Request:
"{user_message}"

Execution Result:
{result_text}

Execution Logs (last 30 stdout lines):
{logs_text}

Please evaluate whether this execution result meets the user's request.
Focus on whether the task was actually completed, not just whether code ran successfully.
"""
        
        return prompt
    
    def quick_validation(
        self,
        execution_result: Dict[str, Any]
    ) -> bool:
        """
        Quick rule-based validation for obvious failures.
        
        Returns True if result seems obviously valid, False if clearly invalid.
        Used as a fast pre-check before LLM evaluation.
        """
        if not execution_result:
            return False
        
        # Check for explicit error status
        if execution_result.get("status") == "error":
            return False
        
        # Check for empty results
        if execution_result.get("status") == "success" and not any(
            key != "status" for key in execution_result.keys()
        ):
            return False
        
        # Passed basic checks
        return True
