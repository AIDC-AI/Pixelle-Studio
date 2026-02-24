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
New tool set - Step 1 implementation.
Contains tool schemas and handlers.
"""
from typing import Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentContext:
    """Agent context"""
    user_id: str = None
    session_id: str = ""
    script_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "scripts" / "default")
    backend_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)


# ============================================================================
# Tool Schemas (OpenAI Function Calling format)
# ============================================================================

TOOL_SCHEMAS_NEW = [
    # 1. shell_exec (persistent session - most important)
    {
        "type": "function",
        "function": {
            "name": "shell_exec",
            "description": """Execute commands in a persistent session (variables and state are preserved).
            
Key features:
- Variable persistence: variables are preserved between calls
- Auto-managed: no need to manually create/close sessions
- Multi-language support: bash, python, ipython
- Error recovery: auto-restart after session crash

Use cases:
1. Multi-step data processing (need to preserve variables)
2. Python interactive analysis (import once, use multiple times)
3. Need to preserve working directory and environment

Workflow examples:
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

Recommendations:
- Multi-step tasks -> shell_exec
- One-off commands -> exec
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
                        "description": "Shell type, default: bash",
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
            "description": """Read file content.
            
Usage recommendations:
- Skill files: read all content directly
- Small user files (< 1000 lines): read directly
- Large user files: first check size with exec("wc -l file"), then decide

Note: Large files will show a warning, but still return full content. For large data files, it's recommended to use exec command to view partial content.
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
1. write_file("script.py", "code content...")
2. exec("python script.py")

For short code, you can execute directly:
- exec("python -c 'print(123)'")
- exec("echo 'hello' > file.txt")

If parameters are too long and cause errors, you can:
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
            "description": """Execute a one-off command (non-persistent).
            
Supported commands:
- Bash commands: ls -la, cat file.txt, grep pattern file
- Short Python code: python -c "print('hello')"
- Python scripts: python script.py

Execution strategy:
- Short commands (1 line): execute directly
- Long code: first use write_file to create a script, then execute

Background execution:
- For long-running tasks (> 30s), use background=True
- Background tasks return session_id, queryable via process tool

Important: each exec call is a new process, variables are NOT preserved!
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
                        "description": "Working directory (optional, defaults to user script directory)"
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

Usage recommendations:
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
            "description": """Search file content (supports regex).
            
Use cases:
- Find function definitions in code
- Search for keywords in configuration files
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
            "description": """Find files (by filename).
            
Use cases:
- Find specific types of files (*.py, *.csv)
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
            
Use cases:
- View files in working directory
- Confirm if a file exists
- Browse project structure

Examples:
ls()  # List current directory
ls("data/")  # List data directory
ls(".", recursive=True)  # Recursively list all files
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
- list: List all background processes
- status: Query the status of a specific process
- logs: Get the output logs of a process
- kill: Terminate a specific process

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
# Tool Handlers
# ============================================================================

from app.tools import (
    read_file,
    write_file,
    edit_file,
    exec_command,
    process_manage,
    shell_exec,
    shell_session_manage,
    grep,
    find,
    ls
)

TOOL_HANDLERS_NEW: Dict[str, Any] = {
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
