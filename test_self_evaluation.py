"""Simple test script to verify self-evaluation system components."""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.context.models import ErrorInfo, EvaluationResult, IterationRecord, ExecutionContext
from app.context.context_manager import ContextManager
from app.evaluation.error_evaluator import RuntimeErrorEvaluator
from datetime import datetime


async def test_context_manager():
    """Test context manager basic functionality."""
    print("\n=== Testing Context Manager ===")
    
    # Create context manager with temp storage
    import tempfile
    temp_dir = tempfile.mkdtemp()
    from app.context.storage import FileStorageBackend
    storage = FileStorageBackend(base_dir=temp_dir)
    manager = ContextManager(storage_backend=storage)
    
    # Initialize context
    ctx = await manager.initialize_context(
        chat_id="test_123",
        user_message="Test request",
        selected_tools=[{"name": "test_tool"}],
        max_iterations=3
    )
    print(f"✓ Created context: {ctx.chat_id}")
    
    # Create and store iteration
    iteration = IterationRecord(
        iteration_id=1,
        timestamp=datetime.now(),
        script_content="print('hello')",
        script_path="/tmp/test.py",
        execution_status="success"
    )
    await manager.store_iteration("test_123", iteration)
    print(f"✓ Stored iteration {iteration.iteration_id}")
    
    # Retrieve context
    loaded_ctx = await manager.get_context("test_123")
    print(f"✓ Loaded context with {len(loaded_ctx.iterations)} iterations")
    
    # Build summary
    summary = manager.build_context_summary(loaded_ctx)
    print(f"✓ Generated context summary ({len(summary)} chars)")
    print(f"   Preview: {summary[:100]}...")
    
    # Cleanup
    await manager.delete_context("test_123")
    print("✓ Cleaned up test context")
    
    return True


async def test_error_evaluator():
    """Test error evaluator."""
    print("\n=== Testing Error Evaluator ===")
    
    evaluator = RuntimeErrorEvaluator()
    
    # Test syntax error
    logs = [
        {"stream": "stderr", "content": "  File \"test.py\", line 5"},
        {"stream": "stderr", "content": "    print('hello'"},
        {"stream": "stderr", "content": "                 ^"},
        {"stream": "stderr", "content": "SyntaxError: unexpected EOF while parsing"}
    ]
    
    error_info = await evaluator.evaluate_error(logs, "print('hello'")
    if error_info:
        print(f"✓ Detected error type: {error_info.error_type}")
        print(f"  Message: {error_info.error_message}")
        print(f"  Line: {error_info.error_line}")
    else:
        print("✗ Failed to detect error")
        return False
    
    # Test import error
    import_logs = [
        {"stream": "stderr", "content": "Traceback (most recent call last):"},
        {"stream": "stderr", "content": "  File \"test.py\", line 1, in <module>"},
        {"stream": "stderr", "content": "    import nonexistent_module"},
        {"stream": "stderr", "content": "ModuleNotFoundError: No module named 'nonexistent_module'"}
    ]
    
    import_error = await evaluator.evaluate_error(import_logs, "import nonexistent_module")
    if import_error and import_error.error_type == "import_error":
        print(f"✓ Correctly classified import error")
    else:
        print("✗ Failed to classify import error")
        return False
    
    return True


async def test_data_models():
    """Test data model serialization."""
    print("\n=== Testing Data Models ===")
    
    # Test ErrorInfo
    error = ErrorInfo(
        error_type="runtime_error",
        error_message="Division by zero",
        traceback="Traceback...",
        error_line=42
    )
    data = error.to_dict()
    restored = ErrorInfo.from_dict(data)
    assert restored.error_type == error.error_type
    print("✓ ErrorInfo serialization works")
    
    # Test EvaluationResult
    eval_result = EvaluationResult(
        meets_requirement=False,
        confidence_score=0.75,
        evaluation_reason="Missing output",
        missing_aspects=["output_file"]
    )
    data = eval_result.to_dict()
    restored = EvaluationResult.from_dict(data)
    assert restored.confidence_score == eval_result.confidence_score
    print("✓ EvaluationResult serialization works")
    
    # Test IterationRecord
    iteration = IterationRecord(
        iteration_id=1,
        timestamp=datetime.now(),
        script_content="test",
        script_path="/tmp/test.py",
        execution_status="success",
        error_info=error,
        evaluation=eval_result
    )
    data = iteration.to_dict()
    restored = IterationRecord.from_dict(data)
    assert restored.iteration_id == iteration.iteration_id
    assert restored.error_info.error_type == error.error_type
    print("✓ IterationRecord serialization works")
    
    # Test ExecutionContext
    ctx = ExecutionContext(
        chat_id="test",
        user_message="Test",
        selected_tools=[],
        iterations=[iteration]
    )
    data = ctx.to_dict()
    restored = ExecutionContext.from_dict(data)
    assert restored.chat_id == ctx.chat_id
    assert len(restored.iterations) == 1
    print("✓ ExecutionContext serialization works")
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Self-Evaluation System Component Tests")
    print("=" * 60)
    
    try:
        # Run tests
        result1 = await test_data_models()
        result2 = await test_error_evaluator()
        result3 = await test_context_manager()
        
        all_passed = result1 and result2 and result3
        
        print("\n" + "=" * 60)
        if all_passed:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")
        print("=" * 60)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
