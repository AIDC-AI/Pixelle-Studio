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
Security module - path and command whitelist validation
"""
from pathlib import Path
from typing import Tuple, Optional
import shlex
import logging

logger = logging.getLogger(__name__)


# Command whitelist
ALLOWED_COMMANDS = {
    # Read operations
    "cat", "head", "tail", "less", "more",
    "grep", "egrep", "fgrep", "ag", "rg",
    "find", "ls", "tree", "du", "stat",
    "wc", "cut", "sort", "uniq", "diff",
    
    # Basic commands
    "echo", "pwd", "cd", "mkdir", "touch", "cp", "mv",
    
    # Python
    "python", "python3", "pip", "pip3",
    
    # Other tools
    "git", "curl", "wget", "jq", "awk", "sed",
    
    # Shell
    "bash", "sh", "zsh"
}

# Command blocklist (Phase 1: delete operations and package installs prohibited)
BLOCKED_COMMANDS = {
    # Delete operations
    "rm", "rmdir", "unlink", "del",
    
    # Dangerous commands
    "sudo", "su", "chmod", "chown", "chgrp",
    "kill", "pkill", "killall",
    "dd", "mkfs", "fdisk", "parted",
    
    # Network dangerous
    "nc", "netcat", "nmap",
    
    # System
    "reboot", "shutdown", "halt", "poweroff", "init",
    
    # Package management (users cannot install packages)
    "pip", "pip3", "easy_install", "conda",
    "npm", "yarn", "gem", "cargo"
}


def validate_path(
    path: str, 
    user_id: Optional[str], 
    operation: str = "read",
    script_dir: Optional[Path] = None
) -> Path:
    """
    Validate and resolve path.
    
    Args:
        path: File path
        user_id: User ID
        operation: Action type ("read" | "write")
        script_dir: Optional script directory (usually context.script_dir, includes date subdirectory)
    
    Returns:
        Resolved absolute path
    
    Raises:
        PermissionError: Path not allowed
    
    Rules:
        - Read: Allowed to access skills/ (all skill directories) and scripts/{user_id}/
        - Write: Only allowed scripts/{user_id}/
        - Prohibited: System directories, other user directories, path traversal
    """
    # Get backend root directory
    # security.py is under app/tools/, need to go up 2 levels to backend/
    backend_root = Path(__file__).parent.parent.parent
    
    # ✅ Prefer the passed script_dir (with date subdirectory)
    # If not provided, use old path without date (backward compatible)
    if script_dir:
        user_scripts_dir = script_dir
        # Parent of user directory (for permission checks)
        user_scripts_parent = backend_root / "scripts" / (user_id or "default")
    else:
        # Backward compatible: path without date
        user_scripts_dir = backend_root / "scripts" / (user_id or "default")
        user_scripts_parent = user_scripts_dir
    
    # Skills directory (including default and user-owned)
    skills_root = backend_root / "skills"
    default_skills_dir = skills_root / "default"
    user_skills_dir = skills_root / (user_id or "default")
    
    # Resolve path
    if Path(path).is_absolute():
        resolved = Path(path).resolve()
    else:
        # Special handling: if path starts with "skills/", resolve based on backend_root
        # So LLM can use relative paths like "skills/default/pdf/SKILL.md"
        if path.startswith("skills/") or path.startswith("skills\\"):
            resolved = (backend_root / path).resolve()
        else:
            # Other relative paths based on user working directory
            resolved = (user_scripts_dir / path).resolve()
    
    # Rule 1: Write operations only in user directory (including date subdirectories)
    if operation == "write":
        if not _is_subpath(resolved, user_scripts_parent):
            raise PermissionError(
                f"Write denied: can only write to your working directory\n"
                f"Allowed: {user_scripts_parent}\n"
                f"Attempted: {resolved}"
            )
        return resolved
    
    # Rule 2: Read operations can access skills (all subdirectories) and user working directory (including date subdirectories)
    if operation == "read":
        allowed_dirs = [
            user_scripts_parent,   # User working directory (including all date subdirectories)
            skills_root,           # All skills (including subdirectories)
        ]
        
        if any(_is_subpath(resolved, allowed) for allowed in allowed_dirs):
            return resolved
        
        raise PermissionError(
            f"Read denied: can only read skills directory or your working directory\n"
            f"Allowed directories:\n"
            f"  - Working directory: {user_scripts_parent}\n"
            f"  - Skills: {skills_root} (and all subdirectories)\n"
            f"Attempted to access: {resolved}"
        )
    
    raise ValueError(f"Unknown operation type: {operation}")


def validate_command(command: str, user_id: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate if command is safe.
    
    Args:
        command: Command to execute
        user_id: User ID
    
    Returns:
        (is_safe, error_message)
        - is_safe: Whether command is safe
        - error_message: Error message if unsafe
    """
    # 1. Parse command
    try:
        tokens = shlex.split(command)
    except ValueError as e:
        return False, f"Command parse failed: {e}"
    
    if not tokens:
        return False, "Empty command"
    
    # Extract main command
    main_command = tokens[0]
    cmd_name = Path(main_command).name
    
    # 2. Check blocklist
    if cmd_name in BLOCKED_COMMANDS:
        return False, (
            f"Command '{cmd_name}' is blocked\n"
            f"Reason: this command may cause system damage or data loss\n"
            f"Note: Phase 1 does not support delete and system management operations"
        )
    
    # 2.5 Special check: python -m pip bypass
    if cmd_name in ["python", "python3"]:
        # Check for -m pip arguments
        if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] in ["pip", "pip3"]:
            return False, (
                f"Using 'python -m pip' to install packages is prohibited\n"
                f"Reason: current environment is shared, does not support user package installation\n"
                f"Note: contact admin if you need specific packages"
            )
    
    # 3. Check allowlist (optional, currently using lenient policy)
    # if cmd_name not in ALLOWED_COMMANDS:
    #     return False, f"Command '{cmd_name}' is not in allowed list"
    
    # 4. Check dangerous patterns (relaxed, && and || allowed)
    dangerous_patterns = [
        (";", "Command injection risk"),
        # && and || are common features, allowed
        # "|" and ">" allowed (pipes and redirects are common features)
    ]
    
    for pattern, reason in dangerous_patterns:
        if pattern in command:
            # But allow inside strings
            if f'"{pattern}"' in command or f"'{pattern}'" in command:
                continue
            return False, f"Command contains dangerous character '{pattern}' ({reason})"
    
    # 5. Check path arguments (if there are file paths)
    for token in tokens[1:]:
        if token.startswith("-"):
            continue  # Option argument, skip
        
        # Check if it looks like a path
        if "/" in token or "\\" in token or token.endswith((".txt", ".py", ".csv", ".json")):
            try:
                # Try to validate path
                validate_path(token, user_id, operation="read")
            except PermissionError:
                # Path validation failed, but not necessarily an error (may be argument, not path)
                # Log warning but allow execution
                logger.warning(f"Command contains potentially invalid path: {token}")
    
    return True, None


def _is_subpath(path: Path, parent: Path) -> bool:
    """
    Check if path is under parent directory.
    
    Args:
        path: Path to check
        parent: Parent directory
    
    Returns:
        True if path is under parent
    """
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def get_user_workdir(user_id: Optional[str]) -> Path:
    """
    Get user working directory.
    
    Args:
        user_id: User ID
    
    Returns:
        Absolute path of user working directory
    """
    # security.py is under app/tools/, need to go up 2 levels to backend/
    backend_root = Path(__file__).parent.parent.parent
    workdir = backend_root / "scripts" / (user_id or "default")
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir

