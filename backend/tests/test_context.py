"""Unit tests for context management system."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.context.models import (
    ErrorInfo,
    EvaluationResult,
    RevisionAdvice,
    IterationRecord,
    ExecutionContext
)
from app.context.storage import FileStorageBackend
from app.context.context_manager import ContextManager


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage_backend(temp_storage_dir):
    """Create a file storage backend with temp directory."""
    return FileStorageBackend(base_dir=temp_storage_dir)


@pytest.fixture
def context_manager(storage_backend):
    """Create a context manager with temp storage."""
    return ContextManager(storage_backend=storage_backend)


class TestDataModels:
    """Test data model serialization/deserialization."""
    
    def test_error_info_serialization(self):
        """Test ErrorInfo to_dict and from_dict."""
        error = ErrorInfo(
            error_type="syntax_error",
            error_message="invalid syntax",
            traceback="Traceback...",
            error_line=42
        )
        
        data = error.to_dict()
        restored = ErrorInfo.from_dict(data)
        
        assert restored.error_type == error.error_type
        assert restored.error_message == error.error_message
        assert restored.error_line == error.error_line
    
    def test_evaluation_result_serialization(self):
        """Test EvaluationResult to_dict and from_dict."""
        eval_result = EvaluationResult(
            meets_requirement=False,
            confidence_score=0.6,
            evaluation_reason="Missing required field",
            missing_aspects=["field1", "field2"]
        )
        
        data = eval_result.to_dict()
        restored = EvaluationResult.from_dict(data)
        
        assert restored.meets_requirement == eval_result.meets_requirement
        assert restored.confidence_score == eval_result.confidence_score
        assert restored.missing_aspects == eval_result.missing_aspects
    
    def test_iteration_record_serialization(self):
        """Test IterationRecord to_dict and from_dict."""
        iteration = IterationRecord(
            iteration_id=1,
            timestamp=datetime.now(),
            script_content="print('hello')",
            script_path="/tmp/script.py",
            execution_status="success",
            execution_logs=[{"type": "log", "content": "hello"}],
            execution_result={"status": "ok"}
        )
        
        data = iteration.to_dict()
        restored = IterationRecord.from_dict(data)
        
        assert restored.iteration_id == iteration.iteration_id
        assert restored.script_content == iteration.script_content
        assert restored.execution_status == iteration.execution_status


class TestFileStorageBackend:
    """Test file storage backend."""
    
    @pytest.mark.asyncio
    async def test_save_and_load_iteration(self, storage_backend):
        """Test saving and loading iteration records."""
        chat_id = "test_chat_123"
        iteration = IterationRecord(
            iteration_id=1,
            timestamp=datetime.now(),
            script_content="print('test')",
            script_path="/tmp/test.py",
            execution_status="success"
        )
        
        # Save
        await storage_backend.save_iteration(chat_id, iteration)
        
        # Verify file exists
        expected_path = storage_backend._get_iteration_path(chat_id, 1)
        assert expected_path.exists()
    
    @pytest.mark.asyncio
    async def test_save_and_load_context(self, storage_backend):
        """Test saving and loading complete context."""
        context = ExecutionContext(
            chat_id="test_chat_456",
            user_message="Test request",
            selected_tools=[{"name": "tool1"}],
            max_iterations=3
        )
        
        # Save metadata
        await storage_backend.save_context_metadata(context)
        
        # Add iterations
        for i in range(1, 3):
            iteration = IterationRecord(
                iteration_id=i,
                timestamp=datetime.now(),
                script_content=f"# Iteration {i}",
                script_path=f"/tmp/script_{i}.py",
                execution_status="success"
            )
            await storage_backend.save_iteration(context.chat_id, iteration)
        
        # Load
        loaded_context = await storage_backend.load_context(context.chat_id)
        
        assert loaded_context is not None
        assert loaded_context.chat_id == context.chat_id
        assert loaded_context.user_message == context.user_message
        assert len(loaded_context.iterations) == 2
    
    @pytest.mark.asyncio
    async def test_delete_context(self, storage_backend):
        """Test deleting a context."""
        chat_id = "test_chat_789"
        context = ExecutionContext(
            chat_id=chat_id,
            user_message="Test",
            selected_tools=[]
        )
        
        await storage_backend.save_context_metadata(context)
        
        # Verify exists
        assert storage_backend._get_context_dir(chat_id).exists()
        
        # Delete
        await storage_backend.delete_context(chat_id)
        
        # Verify deleted
        assert not storage_backend._get_context_dir(chat_id).exists()


class TestContextManager:
    """Test context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_initialize_context(self, context_manager):
        """Test initializing a new context."""
        context = await context_manager.initialize_context(
            chat_id="test_init",
            user_message="Hello",
            selected_tools=[{"name": "tool1"}],
            max_iterations=5
        )
        
        assert context.chat_id == "test_init"
        assert context.user_message == "Hello"
        assert context.max_iterations == 5
        assert context.current_iteration == 0
    
    @pytest.mark.asyncio
    async def test_store_and_get_iteration(self, context_manager):
        """Test storing and retrieving iterations."""
        # Initialize context
        context = await context_manager.initialize_context(
            chat_id="test_iter",
            user_message="Test",
            selected_tools=[]
        )
        
        # Create iteration
        iteration = IterationRecord(
            iteration_id=1,
            timestamp=datetime.now(),
            script_content="print('test')",
            script_path="/tmp/test.py",
            execution_status="success"
        )
        
        # Store
        await context_manager.store_iteration("test_iter", iteration)
        
        # Retrieve
        loaded_context = await context_manager.get_context("test_iter")
        assert len(loaded_context.iterations) == 1
        assert loaded_context.iterations[0].iteration_id == 1
    
    @pytest.mark.asyncio
    async def test_update_context_status(self, context_manager):
        """Test updating context status."""
        context = await context_manager.initialize_context(
            chat_id="test_status",
            user_message="Test",
            selected_tools=[]
        )
        
        # Update status
        await context_manager.update_context_status(
            "test_status",
            status="running",
            current_iteration=1
        )
        
        # Verify
        loaded = await context_manager.get_context("test_status")
        assert loaded.status == "running"
        assert loaded.current_iteration == 1
    
    def test_build_context_summary_first_iteration(self, context_manager):
        """Test context summary for first iteration."""
        context = ExecutionContext(
            chat_id="test_summary",
            user_message="List my files",
            selected_tools=[{"name": "google_drive"}, {"name": "slack"}],
            current_iteration=0
        )
        
        summary = context_manager.build_context_summary(context)
        
        assert "List my files" in summary
        assert "google_drive" in summary
        assert "first attempt" in summary
    
    def test_build_context_summary_with_history(self, context_manager):
        """Test context summary with previous iterations."""
        context = ExecutionContext(
            chat_id="test_summary_hist",
            user_message="List my files",
            selected_tools=[{"name": "google_drive"}],
            current_iteration=1
        )
        
        # Add previous iteration with error
        prev_iteration = IterationRecord(
            iteration_id=1,
            timestamp=datetime.now(),
            script_content="print('test')",
            script_path="/tmp/test.py",
            execution_status="runtime_error",
            error_info=ErrorInfo(
                error_type="import_error",
                error_message="No module named 'requests'",
                traceback="Traceback..."
            )
        )
        context.iterations.append(prev_iteration)
        
        summary = context_manager.build_context_summary(context)
        
        assert "iteration 2" in summary.lower()
        assert "import_error" in summary
        assert "No module named 'requests'" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
