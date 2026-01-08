"""Data models for execution context and iteration tracking."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


@dataclass
class ErrorInfo:
    """Error information from script execution."""
    error_type: str  # syntax_error, import_error, runtime_error, tool_error, type_error
    error_message: str
    traceback: str
    error_line: Optional[int] = None
    error_column: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorInfo":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class EvaluationResult:
    """Result evaluation from LLM validator."""
    meets_requirement: bool  # Whether result meets user's needs
    confidence_score: float  # 0.0-1.0
    evaluation_reason: str
    missing_aspects: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationResult":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class RevisionAdvice:
    """Script revision advice from advisor."""
    should_revise: bool
    revision_type: str  # fix_error, improve_logic, add_missing
    specific_suggestions: List[str]
    llm_prompt: str  # Prompt for LLM to generate revised script
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevisionAdvice":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class IterationRecord:
    """Record of a single iteration in the evaluation loop."""
    iteration_id: int
    timestamp: datetime
    
    # Input
    script_content: str
    script_path: str
    
    # Execution result
    execution_status: str  # success, runtime_error, validation_failed
    execution_logs: List[Dict[str, str]] = field(default_factory=list)
    execution_result: Optional[Dict[str, Any]] = None
    
    # Error information
    error_info: Optional[ErrorInfo] = None
    
    # Evaluation result
    evaluation: Optional[EvaluationResult] = None
    
    # Revision advice
    revision_advice: Optional[RevisionAdvice] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "iteration_id": self.iteration_id,
            "timestamp": self.timestamp.isoformat(),
            "script_content": self.script_content,
            "script_path": self.script_path,
            "execution_status": self.execution_status,
            "execution_logs": self.execution_logs,
            "execution_result": self.execution_result,
            "error_info": self.error_info.to_dict() if self.error_info else None,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "revision_advice": self.revision_advice.to_dict() if self.revision_advice else None
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IterationRecord":
        """Create from dictionary."""
        return cls(
            iteration_id=data["iteration_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            script_content=data["script_content"],
            script_path=data["script_path"],
            execution_status=data["execution_status"],
            execution_logs=data.get("execution_logs", []),
            execution_result=data.get("execution_result"),
            error_info=ErrorInfo.from_dict(data["error_info"]) if data.get("error_info") else None,
            evaluation=EvaluationResult.from_dict(data["evaluation"]) if data.get("evaluation") else None,
            revision_advice=RevisionAdvice.from_dict(data["revision_advice"]) if data.get("revision_advice") else None
        )


@dataclass
class ExecutionContext:
    """Complete execution context for a chat session."""
    chat_id: str
    user_message: str
    selected_tools: List[Dict[str, Any]]
    
    # File URLs uploaded by user
    file_urls: List[str] = field(default_factory=list)
    
    # Iteration history
    iterations: List[IterationRecord] = field(default_factory=list)
    
    # Configuration
    max_iterations: int = 3
    current_iteration: int = 0
    
    # Status
    status: str = "initializing"  # initializing, running, evaluating, success, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chat_id": self.chat_id,
            "user_message": self.user_message,
            "selected_tools": self.selected_tools,
            "file_urls": self.file_urls,
            "iterations": [iter.to_dict() for iter in self.iterations],
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """Create from dictionary."""
        return cls(
            chat_id=data["chat_id"],
            user_message=data["user_message"],
            selected_tools=data["selected_tools"],
            file_urls=data.get("file_urls", []),
            iterations=[IterationRecord.from_dict(iter_data) for iter_data in data.get("iterations", [])],
            max_iterations=data.get("max_iterations", 3),
            current_iteration=data.get("current_iteration", 0),
            status=data.get("status", "initializing")
        )
    
    def get_latest_iteration(self) -> Optional[IterationRecord]:
        """Get the most recent iteration record."""
        return self.iterations[-1] if self.iterations else None
