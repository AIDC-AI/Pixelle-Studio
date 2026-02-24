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
File operation tools - read_file, write_file
"""
from pathlib import Path
from typing import Optional
import json
import asyncio
import logging

from .security import validate_path

logger = logging.getLogger(__name__)


async def read_file(
    context,  # AgentContext
    path: str,
    encoding: str = "utf-8"
) -> str:
    """
    Read file contents.
    
    Args:
        context: AgentContext
        path: File path
        encoding: File encoding
    
    Returns:
        File content or error message
    """
    try:
        # ✅ Security check, pass script_dir to support date subdirectory
        resolved_path = validate_path(path, context.user_id, operation="read", script_dir=context.script_dir)
        
        # Check if file exists
        if not resolved_path.exists():
            # Provide more detailed error info
            return json.dumps({
                "status": "error",
                "error": f"File not found: {path}",
                "resolved_path": str(resolved_path),
                "suggestion": f"Verify the file path. Working directory: {resolved_path.parent}"
            }, ensure_ascii=False)
        
        if not resolved_path.is_file():
            return json.dumps({
                "status": "error",
                "error": f"Not a file: {path}"
            }, ensure_ascii=False)
        
        # Async read file
        content = await asyncio.to_thread(
            resolved_path.read_text,
            encoding=encoding
        )
        
        # Check if it is a skill file
        is_skill_file = "skills/" in str(resolved_path) or "/skills/" in str(resolved_path)
        
        # Statistics
        lines = content.count('\n') + 1
        size = len(content)
        
        # Large file warning (but still returns full content)
        warning = ""
        if not is_skill_file and lines > 1000:
            warning = (
                f"⚠️ File is large ({lines} lines, {size} bytes)\n\n"
                f"Suggestion: for large data files, use exec command to view partial content:\n"
                f"  - exec(\"head -n 100 {path}\")  # View first 100 lines\n"
                f"  - exec(\"wc -l {path}\")        # Count lines\n"
                f"  - exec(\"tail -n 100 {path}\")  # View last 100 lines\n\n"
                f"---\n\n"
            )
        
        logger.info(f"[read_file] {path} ({lines} lines, {size} bytes)")
        
        return warning + content
        
    except PermissionError as e:
        logger.error(f"[read_file] Permission denied: {path} - {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[read_file] Error reading {path}: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Failed to read file: {e}"
        }, ensure_ascii=False)


async def write_file(
    context,  # AgentContext
    path: str,
    content: str,
    encoding: str = "utf-8",
    notify_frontend: bool = False
) -> str:
    """
    Create or overwrite a file.
    
    Args:
        context: AgentContext
        path: File path
        content: File content
        encoding: File encoding
        notify_frontend: Whether to notify frontend (default False, only True for final user files)
    
    Returns:
        JSON formatted result
    """
    try:
        # ✅ If relative path, resolve based on context.script_dir (with date subdirectory)
        # If absolute path, keep unchanged
        if not Path(path).is_absolute():
            # Relative path relative to current working directory (with date)
            full_path = str(context.script_dir / path)
        else:
            full_path = path
        
        # ✅ Security check, pass script_dir to support date subdirectory
        resolved_path = validate_path(full_path, context.user_id, operation="write", script_dir=context.script_dir)
        
        # Create parent directory
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ✅ Handle same-name file conflict: auto-rename
        original_path = resolved_path
        if resolved_path.exists():
            stem = resolved_path.stem
            suffix = resolved_path.suffix
            counter = 2
            while resolved_path.exists():
                resolved_path = resolved_path.parent / f"{stem}_{counter}{suffix}"
                counter += 1
            
            logger.info(f"[write_file] File exists, auto-renaming: {original_path.name} -> {resolved_path.name}")
        
        # Async write file
        await asyncio.to_thread(
            resolved_path.write_text,
            content,
            encoding=encoding
        )
        
        # Statistics
        lines = content.count('\n') + 1
        size = len(content)
        
        # Check if it was renamed
        was_renamed = (resolved_path != original_path)
        
        logger.info(f"[write_file] {resolved_path.name} ({lines} lines, {size} bytes) notify_frontend={notify_frontend}")
        
        result = {
            "status": "success",
            "path": str(resolved_path),
            "relative_path": path,  # Original relative path
            "actual_filename": resolved_path.name,  # Actual filename (may be renamed)
            "renamed": was_renamed,  # ✅ Always return this field
            "size": size,
            "lines": lines,
            "notify_frontend": notify_frontend,  # ✅ Mark whether to notify frontend
            "message": f"File written: {resolved_path.name} ({lines} lines, {size} bytes)"
        }
        
        # If renamed, add extra info
        if was_renamed:
            result["original_name"] = original_path.name
            result["message"] = f"File written (renamed): {original_path.name} -> {resolved_path.name} ({lines} lines, {size} bytes)"
        
        return json.dumps(result, ensure_ascii=False)
        
    except PermissionError as e:
        logger.error(f"[write_file] Permission denied: {path} - {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[write_file] Error writing {path}: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Failed to write file: {e}"
        }, ensure_ascii=False)

