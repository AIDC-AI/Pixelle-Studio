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
Auxiliary tools - edit_file, grep, find, ls
"""
import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Optional, List

from .security import validate_path, get_user_workdir

import logging
logger = logging.getLogger(__name__)


async def edit_file(
    context,  # AgentContext
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False
) -> str:
    """
    Edit a file (string replacement).
    
    Args:
        context: AgentContext
        path: File path
        old_string: String to replace
        new_string: Replacement string
        replace_all: Replace all matches (default: only first)
    
    Returns:
        JSON formatted result
    """
    try:
        # ✅ Security check, pass script_dir to support date subdirectory
        resolved_path = validate_path(path, context.user_id, operation="write", script_dir=context.script_dir)
        
        # Check if file exists
        if not resolved_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"File not found: {path}"
            }, ensure_ascii=False)
        
        # Read file
        content = await asyncio.to_thread(
            resolved_path.read_text,
            encoding='utf-8'
        )
        
        # Check if old_string exists
        if old_string not in content:
            # Find similar content
            lines = content.split('\n')
            similar_lines = [
                (i+1, line) for i, line in enumerate(lines)
                if old_string[:20] in line or any(
                    word in line for word in old_string.split() if len(word) > 3
                )
            ]
            
            error_msg = f"String to replace not found\n\n"
            if similar_lines:
                error_msg += "Possible similar lines:\n"
                for line_no, line in similar_lines[:3]:
                    error_msg += f"  Line {line_no}: {line[:100]}\n"
            
            return json.dumps({
                "status": "error",
                "error": error_msg
            }, ensure_ascii=False)
        
        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            count = content.count(old_string)
        else:
            # Only replace first occurrence
            new_content = content.replace(old_string, new_string, 1)
            count = 1
        
        # Write file
        await asyncio.to_thread(
            resolved_path.write_text,
            new_content,
            encoding='utf-8'
        )
        
        logger.info(f"[edit_file] {path}: Replaced {count} occurrences")
        
        return json.dumps({
            "status": "success",
            "path": str(resolved_path),
            "replacements": count,
            "message": f"Replaced {count} occurrences"
        }, ensure_ascii=False)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[edit_file] Error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Failed to edit file: {e}"
        }, ensure_ascii=False)


async def grep(
    context,  # AgentContext
    pattern: str,
    path: str,
    case_insensitive: bool = False,
    recursive: bool = False,
    context_lines: int = 0
) -> str:
    """
    Search file content.
    
    Args:
        context: AgentContext
        pattern: Search pattern (supports regex)
        path: File or directory path
        case_insensitive: Case insensitive
        recursive: Recursive directory search
        context_lines: Number of context lines to display
    
    Returns:
        JSON formatted result
    """
    try:
        # ✅ Security check, pass script_dir to support date subdirectory
        resolved_path = validate_path(path, context.user_id, operation="read", script_dir=context.script_dir)
        
        if not resolved_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"Path not found: {path}"
            }, ensure_ascii=False)
        
        results = []
        
        if resolved_path.is_file():
            # Search single file
            matches = await _grep_file(
                resolved_path, 
                pattern, 
                case_insensitive, 
                context_lines
            )
            if matches:
                results.append({
                    "file": str(resolved_path),
                    "matches": matches
                })
        
        elif resolved_path.is_dir() and recursive:
            # Recursively search directory
            for file_path in resolved_path.rglob("*"):
                if file_path.is_file():
                    try:
                        matches = await _grep_file(
                            file_path, 
                            pattern, 
                            case_insensitive, 
                            context_lines
                        )
                        if matches:
                            results.append({
                                "file": str(file_path),
                                "matches": matches
                            })
                    except:
                        pass  # Skip unreadable files
        
        else:
            return json.dumps({
                "status": "error",
                "error": "Path must be a file, or use recursive=True to search directory"
            }, ensure_ascii=False)
        
        # Format output
        if not results:
            output = f"No matches found for '{pattern}'"
        else:
            output_lines = []
            for result in results:
                output_lines.append(f"\nFile: {result['file']}")
                for match in result['matches']:
                    output_lines.append(f"  Line {match['line_number']}: {match['line']}")
                    if 'context' in match:
                        for ctx_line in match['context']:
                            output_lines.append(f"       {ctx_line}")
            output = '\n'.join(output_lines)
        
        return json.dumps({
            "status": "success",
            "pattern": pattern,
            "results": results,
            "total_matches": sum(len(r['matches']) for r in results),
            "output": output
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"[grep] Error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Search failed: {e}"
        }, ensure_ascii=False)


async def _grep_file(
    file_path: Path, 
    pattern: str, 
    case_insensitive: bool,
    context_lines: int
) -> List[dict]:
    """Search a single file"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        # Compile regex
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)
        
        matches = []
        for i, line in enumerate(lines):
            if regex.search(line):
                match_info = {
                    "line_number": i + 1,
                    "line": line
                }
                
                # Add context
                if context_lines > 0:
                    context = []
                    for j in range(max(0, i - context_lines), min(len(lines), i + context_lines + 1)):
                        if j != i:
                            context.append(f"{j+1}: {lines[j]}")
                    match_info["context"] = context
                
                matches.append(match_info)
        
        return matches
        
    except Exception:
        return []


async def find(
    context,  # AgentContext
    pattern: str,
    directory: str = "."
) -> str:
    """
    Find files (by filename).
    
    Args:
        context: AgentContext
        pattern: Filename pattern (supports glob, e.g. *.py)
        directory: Search directory
    
    Returns:
        JSON formatted result
    """
    try:
        # ✅ Security check, pass script_dir to support date subdirectory
        resolved_dir = validate_path(directory, context.user_id, operation="read", script_dir=context.script_dir)
        
        if not resolved_dir.exists():
            return json.dumps({
                "status": "error",
                "error": f"Directory not found: {directory}"
            }, ensure_ascii=False)
        
        if not resolved_dir.is_dir():
            return json.dumps({
                "status": "error",
                "error": f"Not a directory: {directory}"
            }, ensure_ascii=False)
        
        # Search using glob
        matches = list(resolved_dir.rglob(pattern))
        
        # Filter and format results
        files = []
        dirs = []
        
        for match in matches:
            rel_path = str(match.relative_to(resolved_dir))
            if match.is_file():
                files.append({
                    "path": str(match),
                    "name": match.name,
                    "size": match.stat().st_size
                })
            elif match.is_dir():
                dirs.append({
                    "path": str(match),
                    "name": match.name
                })
        
        # Format output
        output_lines = []
        if files:
            output_lines.append(f"Files ({len(files)}):")
            for f in files[:20]:  # Limit display count
                output_lines.append(f"  {f['path']}")
        if dirs:
            output_lines.append(f"\nDirectories ({len(dirs)}):")
            for d in dirs[:20]:
                output_lines.append(f"  {d['path']}/")
        
        if not files and not dirs:
            output_lines.append(f"No files or directories matching '{pattern}' found")
        
        return json.dumps({
            "status": "success",
            "pattern": pattern,
            "files": files,
            "dirs": dirs,
            "total": len(files) + len(dirs),
            "output": '\n'.join(output_lines)
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"[find] Error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Find failed: {e}"
        }, ensure_ascii=False)


async def ls(
    context,  # AgentContext
    path: str = ".",
    recursive: bool = False,
    show_hidden: bool = False,
    limit: int = 10,
    pattern: Optional[str] = None
) -> str:
    """
    List directory contents.
    
    Args:
        context: AgentContext
        path: Directory path
        recursive: Recursively list subdirectories
        show_hidden: Show hidden files
        limit: Max entries to return (default 10, to avoid context overflow)
        pattern: Filename filter pattern (supports wildcards, e.g. "*.pdf")
    
    Returns:
        JSON formatted result
    """
    try:
        # ✅ Security check, pass script_dir to support date subdirectory
        resolved_path = validate_path(path, context.user_id, operation="read", script_dir=context.script_dir)
        
        if not resolved_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"Path not found: {path}"
            }, ensure_ascii=False)
        
        if not resolved_path.is_dir():
            # If it's a file, return file info
            stat = resolved_path.stat()
            return json.dumps({
                "status": "success",
                "type": "file",
                "path": str(resolved_path),
                "name": resolved_path.name,
                "size": stat.st_size,
                "output": f"File: {resolved_path.name} ({stat.st_size} bytes)"
            }, ensure_ascii=False)
        
        # List directory contents
        items = []
        
        if recursive:
            # Recursive listing
            for item in resolved_path.rglob("*"):
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # ✅ Apply pattern filter
                if pattern and not item.match(pattern):
                    continue
                
                rel_path = str(item.relative_to(resolved_path))
                stat = item.stat()
                
                items.append({
                    "path": str(item),
                    "name": rel_path,
                    "type": "dir" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None
                })
        else:
            # List current directory only
            for item in resolved_path.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # ✅ Apply pattern filter
                if pattern:
                    import fnmatch
                    if not fnmatch.fnmatch(item.name, pattern):
                        continue
                
                stat = item.stat()
                
                items.append({
                    "path": str(item),
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None
                })
        
        # Sort (directories first, by name)
        items.sort(key=lambda x: (x['type'] != 'dir', x['name']))
        
        # Check if over limit
        total_items = len(items)
        truncated = total_items > limit
        if truncated:
            items = items[:limit]
        
        # Format output
        output_lines = [f"Directory: {resolved_path}"]
        if pattern:
            output_lines[0] += f" (Filter: {pattern})"
        output_lines[0] += "\n"
        
        if truncated:
            output_lines.append(f"⚠️ Warning: Directory contains {total_items} items, only showing first {limit}\n")
            output_lines.append(f"Suggestion: Use pattern parameter to filter, e.g. ls(path='.', pattern='*.pdf', limit=20)\n")
        
        dirs = [i for i in items if i['type'] == 'dir']
        files = [i for i in items if i['type'] == 'file']
        
        if dirs:
            output_lines.append(f"Directories ({len(dirs)}):")
            for d in dirs:
                output_lines.append(f"  {d['name']}/")
        
        if files:
            output_lines.append(f"\nFiles ({len(files)}):")
            for f in files:
                size_str = f"{f['size']:,}" if f['size'] is not None else "?"
                output_lines.append(f"  {f['name']} ({size_str}  bytes)")
        
        if not items:
            output_lines.append("(empty directory)")
        
        result = {
            "status": "success",
            "path": str(resolved_path),
            "items": items,
            "total": len(items),
            "total_all": total_items,  # Actual total count
            "truncated": truncated,  # Whether truncated
            "output": '\n'.join(output_lines)
        }
        
        if pattern:
            result["pattern"] = pattern
        
        return json.dumps(result, ensure_ascii=False)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[ls] Error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Failed to list directory: {e}"
        }, ensure_ascii=False)

