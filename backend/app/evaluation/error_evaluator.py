"""Runtime error evaluator for analyzing script execution failures."""

import re
from typing import Optional, List, Dict, Tuple

from app.context.models import ErrorInfo


class RuntimeErrorEvaluator:
    """Analyzes runtime errors from script execution and classifies them."""
    
    # Error type classification patterns
    ERROR_PATTERNS = {
        "syntax_error": ["SyntaxError"],
        "import_error": ["ImportError", "ModuleNotFoundError"],
        "tool_error": ["call_tool"],  # Errors involving tool calls
        "type_error": ["AttributeError", "TypeError"],
        "value_error": ["KeyError", "ValueError", "IndexError"],
        "runtime_error": []  # Catch-all
    }
    
    async def evaluate_error(
        self,
        execution_logs: List[Dict],
        script_content: str
    ) -> Optional[ErrorInfo]:
        """
        Analyze execution logs to extract and classify errors.
        
        Args:
            execution_logs: List of log entries from script execution
            script_content: The script that was executed
            
        Returns:
            ErrorInfo if an error was found, None otherwise
        """
        # Extract stderr logs
        error_logs = [
            log for log in execution_logs
            if log.get("stream") == "stderr" and log.get("content")
        ]
        
        if not error_logs:
            return None
        
        # Combine error messages
        traceback_text = "\n".join([log["content"] for log in error_logs])
        
        # Classify error
        error_type = self._classify_error(traceback_text)
        
        # Extract error location
        error_line, error_column = self._extract_error_location(traceback_text)
        
        # Extract error message
        error_message = self._extract_error_message(traceback_text)
        
        return ErrorInfo(
            error_type=error_type,
            error_message=error_message,
            traceback=traceback_text,
            error_line=error_line,
            error_column=error_column
        )
    
    def _classify_error(self, traceback: str) -> str:
        """
        Classify the error based on traceback content.
        
        Priority:
        1. Syntax Error (highest priority)
        2. Import Error
        3. Tool Error (if 'call_tool' in traceback)
        4. Type/Attribute Error
        5. Value Error (KeyError, ValueError, etc.)
        6. Runtime Error (catch-all)
        """
        # Check each pattern in priority order
        for error_type, patterns in self.ERROR_PATTERNS.items():
            if error_type == "runtime_error":
                continue  # Skip catch-all
            
            for pattern in patterns:
                if pattern in traceback:
                    # Special case: tool_error requires both call_tool and an error
                    if error_type == "tool_error":
                        if "call_tool" in traceback and any(
                            err in traceback for err in ["Error", "Exception"]
                        ):
                            return "tool_error"
                    else:
                        return error_type
        
        # Default to runtime_error
        return "runtime_error"
    
    def _extract_error_location(self, traceback: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract error line and column from traceback.
        
        Example patterns:
        - File "/path/to/script.py", line 42, in main
        - File "/path/to/script.py", line 42
        """
        # Try to find line number
        line_match = re.search(r'line (\d+)', traceback)
        line_num = int(line_match.group(1)) if line_match else None
        
        # Try to find column (less common, but possible)
        # Python 3.11+ shows column numbers in some cases
        col_match = re.search(r'column (\d+)', traceback)
        col_num = int(col_match.group(1)) if col_match else None
        
        return line_num, col_num
    
    def _extract_error_message(self, traceback: str) -> str:
        """
        Extract the actual error message from traceback.
        
        Typically the last line contains the error message.
        """
        lines = traceback.strip().split("\n")
        
        # The last non-empty line usually contains the error
        for line in reversed(lines):
            line = line.strip()
            if line and "Error" in line or "Exception" in line:
                return line
        
        # Fallback to last line
        return lines[-1] if lines else "Unknown error"
    
    def get_error_context(
        self,
        script_content: str,
        error_line: Optional[int],
        context_lines: int = 3
    ) -> str:
        """
        Extract code context around the error line.
        
        Args:
            script_content: The full script content
            error_line: Line number where error occurred (1-indexed)
            context_lines: Number of lines to show before/after
            
        Returns:
            Formatted code snippet with line numbers
        """
        if error_line is None:
            return ""
        
        lines = script_content.split("\n")
        
        # Calculate range (convert to 0-indexed)
        start_line = max(0, error_line - context_lines - 1)
        end_line = min(len(lines), error_line + context_lines)
        
        # Build context with line numbers
        context_parts = []
        for i in range(start_line, end_line):
            line_num = i + 1
            prefix = ">>> " if line_num == error_line else "    "
            context_parts.append(f"{prefix}{line_num:4d} | {lines[i]}")
        
        return "\n".join(context_parts)
