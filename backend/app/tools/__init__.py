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

"""New tool set - unified export module.
Contains AgentContext, Tool Schemas, Tool Handlers.
"""
from typing import Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================================
# AgentContext - Context
# ============================================================================

@dataclass
class AgentContext:
    """Agent context"""
    user_id: str = None
    session_id: str = ""
    # __init__.py is under app/tools/, need to go up 3 levels to backend/
    script_dir: Path = None
    backend_root: Path = None
    # MCP server configuration (for call_tool injection into execution environment)
    mcp_server_url: str = None
    mcp_server_type: str = "sse"
    
    def __post_init__(self):
        """Auto-set paths after initialization"""
        # If backend_root is not explicitly passed, auto-calculate
        if self.backend_root is None:
            self.backend_root = Path(__file__).parent.parent.parent
        
        # If script_dir is not explicitly passed, auto-calculate based on user_id
        if self.script_dir is None:
            user_subdir = self.user_id if self.user_id else "default"
            
            # Add date subdirectory
            from datetime import date
            today = date.today().isoformat()  # Format: 2026-02-04
            
            self.script_dir = self.backend_root / "scripts" / user_subdir / today
            # Auto-create directory
            self.script_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Tool Schemas (OpenAI Function Calling format)
# ============================================================================

TOOL_SCHEMAS = [
    # 1. shell_exec (persistent session - most important)
    {
        "type": "function",
        "function": {
            "name": "shell_exec",
            "description": """Execute commands in a persistent session (variables and state are preserved).
            
Key features:
- Variable persistence: variables persist across multiple calls
- Auto-managed: no need to manually create/close sessions
- Multi-language support: bash, python, ipython
- Error recovery: auto-restart after session crash

Important: shell_type determines the command format!

**shell_type="bash"**: command is a Bash command
```
Correct:
  shell_exec("ls -la", shell_type="bash")
  shell_exec("python script.py", shell_type="bash")
  shell_exec("python -c 'print(123)'", shell_type="bash")
  shell_exec("echo $HOME", shell_type="bash")

Wrong:
  shell_exec("import pandas", shell_type="bash")  # bash doesn't recognize import
```

**shell_type="python"**: command is pure Python code
```
Correct:
  shell_exec("import pandas as pd", shell_type="python")
  shell_exec("x = 123", shell_type="python")
  shell_exec("print(x)", shell_type="python")

Wrong:
  shell_exec("python -c 'print(123)'", shell_type="python")  # python -c is a bash command
  shell_exec("ls -la", shell_type="python")  # ls is a bash command
```

Workflow example:
```
# Bash session
shell_exec("x=123", shell_type="bash")
shell_exec("echo $x", shell_type="bash")  # Output: 123

# Python session
shell_exec("import pandas as pd", shell_type="python")
shell_exec("df = pd.DataFrame({'a': [1,2,3]})", shell_type="python")
shell_exec("print(df)", shell_type="python")  # df variable still exists
```

Difference from exec:
- exec: new process each time, variables not preserved
- shell_exec: persistent session, variables preserved

Code length limit:
- **Do not execute code longer than 50 lines or 1500 characters in shell_exec**
- Long code must use write_file + exec:
  ```
  write_file("script.py", "...long code...")
  exec("python script.py")
  ```
- Reason: pexpect environment is unstable with long code

Recommendations:
- Multi-step tasks -> shell_exec
- One-time commands -> exec
- Long code/complex scripts -> write_file + exec
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "shell_type": {
                        "type": "string",
                        "enum": ["bash", "python", "ipython"],
                        "description": """Shell type, default: bash
                        
Key: shell_type determines the command format!
- bash: command is a Bash command (e.g. "ls -la", "python script.py", "echo $x")
- python: command is pure Python code (e.g. "import pandas", "x = 123", "print(x)")
- ipython: command is IPython code (supports magic commands)

Common mistakes:
Wrong: shell_type="python" + command="python -c '...'" (python -c is a bash command)
Correct: shell_type="bash" + command="python -c '...'"
Correct: shell_type="python" + command="print('hello')" (pure Python code)
""",
                        "default": "bash"
                    },
                    "new_session": {
                        "type": "boolean",
                        "description": "Force create new session (closes old session), default: False",
                        "default": False
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds, default: 300",
                        "default": 300
                    }
                },
                "required": ["command"]
            }
        }
    },
    
    # 2. read_file
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": """Read file contents.
            
Usage suggestions:
- Skill files: read full content directly
- Small user files (< 1000 lines): read directly
- Large user files: first use exec("wc -l file") to check size, then decide

Note: large files will show a warning but still return full content. For large data files, it's recommended to use exec command to view partial content.
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (relative to working directory or absolute)"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding, default: utf-8",
                        "default": "utf-8"
                    }
                },
                "required": ["path"]
            }
        }
    },
    
    # 3. write_file
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": """Create or overwrite a file.
            
Recommended workflow (multi-step execution):
1. write_file("script.py", "code content...", notify_frontend=false)  # Intermediate file
2. exec("python script.py")  # Generate final files (PDF, Excel, etc.)

notify_frontend parameter:
- false (default): intermediate script file, do not notify frontend
- true: final user file (e.g. manually created config), notify frontend
- **Files generated by exec automatically notify the frontend, no setup needed**

For short code, you can execute directly:
- exec("python -c 'print(123)'")
- exec("echo 'hello' > file.txt")

If parameter is too long and causes errors, you can:
1. Split into multiple small files
2. Use code block format (see documentation)
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding, default: utf-8",
                        "default": "utf-8"
                    },
                    "notify_frontend": {
                        "type": "boolean",
                        "description": "Whether to notify frontend to display this file, default: False (intermediate files hidden)",
                        "default": False
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    
    # 4. exec
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": """Execute a one-time command (non-persistent).
            
Supported commands:
- Bash commands: ls -la, cat file.txt, grep pattern file
- Python short code: python -c "print('hello')"
- Python scripts: python script.py

Execution strategy:
- Short commands (1 line): execute directly
- Long code: create script with write_file first, then execute

Background execution:
- For long-running tasks (> 30s), use background=True
- Background tasks return session_id, check with process tool

Important: each exec is a new process, variables are not preserved!
For multi-step execution and variable persistence, use shell_exec.

Examples:
- exec("ls -la")
- exec("python -c 'import sys; print(sys.version)'")
- exec("python script.py", timeout=300)
- exec("python long_task.py", background=True)
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Working directory (optional, default: user script directory)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds, default: 300",
                        "default": 300
                    },
                    "background": {
                        "type": "boolean",
                        "description": "Run in background, default: False",
                        "default": False
                    }
                },
                "required": ["command"]
            }
        }
    },
    
    # 5. edit_file
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": """Edit a file (string replacement).
            
Use cases:
- Modify specific lines in code
- Correct values in configuration files
- Batch replace content

Usage suggestions:
- old_string must match exactly (including spaces, indentation)
- Recommended to use read_file first to confirm content
- On replacement failure, similar lines will be suggested

Examples:
edit_file("config.py", "DEBUG = False", "DEBUG = True")
edit_file("script.py", "old_func()", "new_func()", replace_all=True)
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "String to replace (must match exactly)"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement string"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all matches, default: False (only first)",
                        "default": False
                    }
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    
    # 6. grep
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": """Search file contents (supports regex).
            
Use cases:
- Find function definitions in code
- Search for keywords in config files
- Locate error message positions

Examples:
grep("def.*main", "script.py")  # Find main function
grep("ERROR", "app.log", case_insensitive=True)
grep("import.*pandas", ".", recursive=True)  # Recursive search
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (supports regex)"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path"
                    },
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "Case insensitive, default: False",
                        "default": False
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recursive directory search, default: False",
                        "default": False
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Context lines to display, default: 0",
                        "default": 0
                    }
                },
                "required": ["pattern", "path"]
            }
        }
    },
    
    # 7. find
    {
        "type": "function",
        "function": {
            "name": "find",
            "description": """Find files by name.
            
Use cases:
- Find specific file types (*.py, *.csv)
- Locate configuration files
- Browse project structure

Examples:
find("*.py")  # Find all Python files
find("config.*")  # Find all config files
find("*test*", "src/")  # Search in src directory
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Filename pattern (supports glob, e.g. *.py)"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Search directory, default: current",
                        "default": "."
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    
    # 8. ls
    {
        "type": "function",
        "function": {
            "name": "ls",
            "description": """List directory contents.
            
Important: default shows only 10 files to avoid context overflow!

Use cases:
- Quickly view a few files
- Use pattern parameter for precise filtering

Must use pattern filter:
- ls(pattern="*.pdf")  # View PDF files only
- ls(pattern="*.py", limit=20)  # First 20 Python files
- find("*.csv")  # Or use find tool

Don't use bare ls() - it returns only 10 files, may not be what you need!
Use ls(pattern="...") or find() for precise lookup.

Examples:
- ls(pattern="*.pdf")  # View PDF files
- ls(pattern="test_*", limit=5)  # First 5 files starting with test
- find("*.csv")  # Better choice
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path, default: current",
                        "default": "."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recursively list subdirectories, default: False",
                        "default": False
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Show hidden files, default: False",
                        "default": False
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max entries to return, default: 10 (avoid context overflow)",
                        "default": 10
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Filename filter pattern (supports wildcards, e.g. '*.pdf', 'test_*'), strongly recommended"
                    }
                },
                "required": []
            }
        }
    },
    
    # 9. process
    {
        "type": "function",
        "function": {
            "name": "process",
            "description": """Manage background processes.
            
Action types:
- list: list all background processes
- status: query status of a specific process
- logs: get process output logs
- kill: terminate a specific process

Examples:
- process(action="list")
- process(action="status", session_id="exec_abc123")
- process(action="logs", session_id="exec_abc123")
- process(action="kill", session_id="exec_abc123")
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "status", "logs", "kill"],
                        "description": "Action type"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Process session ID (not needed for list action)"
                    }
                },
                "required": ["action"]
            }
        }
    }
]


# ============================================================================
# Tool Handlers - import all tool implementations
# ============================================================================

from .security import validate_path, validate_command, get_user_workdir
from .file_ops import read_file, write_file
from .execution import exec_command, process_manage
from .shell_session import shell_exec, shell_session_manage
from .auxiliary import edit_file, grep, find, ls

TOOL_HANDLERS: Dict[str, Any] = {
    "shell_exec": shell_exec,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "grep": grep,
    "find": find,
    "ls": ls,
    "exec": exec_command,
    "process": process_manage,
    "shell_session": shell_session_manage,
}


# ============================================================================
# Export all
# ============================================================================

__all__ = [
    # Context and Schemas
    "AgentContext",
    "TOOL_SCHEMAS",
    "TOOL_HANDLERS",
    
    # Security
    "validate_path",
    "validate_command",
    "get_user_workdir",
    
    # File operations
    "read_file",
    "write_file",
    "edit_file",
    
    # Execution
    "exec_command",
    "process_manage",
    
    # Persistent sessions
    "shell_exec",
    "shell_session_manage",
    
    # Auxiliary tools
    "grep",
    "find",
    "ls",
]
