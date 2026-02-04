"""
新工具集 - 统一导出模块
包含 AgentContext, Tool Schemas, Tool Handlers
"""
from typing import Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================================
# AgentContext - 上下文
# ============================================================================

@dataclass
class AgentContext:
    """Agent 上下文"""
    user_id: str = None
    session_id: str = ""
    # __init__.py 在 app/tools/ 下，需要往上三层到 backend/
    script_dir: Path = None
    backend_root: Path = None
    
    def __post_init__(self):
        """初始化后自动设置路径"""
        # 如果没有显式传递 backend_root，自动计算
        if self.backend_root is None:
            self.backend_root = Path(__file__).parent.parent.parent
        
        # 如果没有显式传递 script_dir，根据 user_id 自动计算
        if self.script_dir is None:
            user_subdir = self.user_id if self.user_id else "default"
            
            # ✅ 添加日期子目录（方案 B）
            from datetime import date
            today = date.today().isoformat()  # 格式: 2026-02-04
            
            self.script_dir = self.backend_root / "scripts" / user_subdir / today
            # 自动创建目录
            self.script_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Tool Schemas (OpenAI Function Calling 格式)
# ============================================================================

TOOL_SCHEMAS = [
    # 1. shell_exec (持久化会话 - 最重要)
    {
        "type": "function",
        "function": {
            "name": "shell_exec",
            "description": """在持久化会话中执行命令（变量和状态会保持）。
            
🌟 关键特性：
- ✅ 变量持久化：多次调用间变量保持
- ✅ 自动管理：无需手动创建/关闭会话
- ✅ 多语言支持：bash, python, ipython
- ✅ 错误恢复：会话崩溃后自动重启

⚠️ 重要：shell_type 决定了 command 的格式！

**shell_type="bash"**: command 是 Bash 命令
```
✅ 正确:
  shell_exec("ls -la", shell_type="bash")
  shell_exec("python script.py", shell_type="bash")
  shell_exec("python -c 'print(123)'", shell_type="bash")
  shell_exec("echo $HOME", shell_type="bash")

❌ 错误:
  shell_exec("import pandas", shell_type="bash")  # bash 不认识 import
```

**shell_type="python"**: command 是纯 Python 代码
```
✅ 正确:
  shell_exec("import pandas as pd", shell_type="python")
  shell_exec("x = 123", shell_type="python")
  shell_exec("print(x)", shell_type="python")

❌ 错误:
  shell_exec("python -c 'print(123)'", shell_type="python")  # python -c 是 bash 命令
  shell_exec("ls -la", shell_type="python")  # ls 是 bash 命令
```

工作流示例：
```
# Bash 会话
shell_exec("x=123", shell_type="bash")
shell_exec("echo $x", shell_type="bash")  # 输出: 123

# Python 会话
shell_exec("import pandas as pd", shell_type="python")
shell_exec("df = pd.DataFrame({'a': [1,2,3]})", shell_type="python")
shell_exec("print(df)", shell_type="python")  # df 变量仍存在
```

vs exec 的区别：
- exec: 每次都是新进程，变量不保持
- shell_exec: 持久化会话，变量保持

⚠️ 代码长度限制：
- **不要在 shell_exec 中执行超过 50 行或 1500 字符的代码**
- 长代码必须使用 write_file + exec 方式：
  ```
  write_file("script.py", "...长代码...")
  exec("python script.py")
  ```
- 原因：pexpect 环境对长代码处理不稳定

建议：
- 多步骤任务 → shell_exec
- 一次性命令 → exec
- 长代码/复杂脚本 → write_file + exec
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令"
                    },
                    "shell_type": {
                        "type": "string",
                        "enum": ["bash", "python", "ipython"],
                        "description": """Shell 类型，默认 bash
                        
⚠️ 关键：shell_type 决定了 command 的格式！
- bash: command 是 Bash 命令（如 "ls -la", "python script.py", "echo $x"）
- python: command 是纯 Python 代码（如 "import pandas", "x = 123", "print(x)"）
- ipython: command 是 IPython 代码（支持魔法命令）

常见错误：
❌ shell_type="python" + command="python -c '...'" （python -c 是 bash 命令）
✅ shell_type="bash" + command="python -c '...'"
✅ shell_type="python" + command="print('hello')" （纯 Python 代码）
""",
                        "default": "bash"
                    },
                    "new_session": {
                        "type": "boolean",
                        "description": "是否强制创建新会话（会关闭旧会话），默认 False",
                        "default": False
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒），默认 300",
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
            "description": """读取文件内容。
            
使用建议：
- Skill 文件：直接读取全部内容
- 用户小文件（< 1000 行）：直接读取
- 用户大文件：先用 exec("wc -l file") 查看大小，再决定

注意：大文件会有警告，但仍返回完整内容。对于大数据文件，建议使用 exec 命令查看部分内容。
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径（相对于工作目录或绝对路径）"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "文件编码，默认 utf-8",
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
            "description": """创建或覆盖文件。
            
推荐工作流（多步执行）：
1. write_file("script.py", "代码内容...", notify_frontend=false)  # 中间文件
2. exec("python script.py")  # 生成最终文件（PDF、Excel等）

⚠️ notify_frontend参数说明：
- false（默认）：中间脚本文件，不通知前端
- true：最终用户文件（如手动创建的配置文件），通知前端
- **exec生成的文件会自动通知前端，无需设置**

对于短代码，可以直接执行：
- exec("python -c 'print(123)'")
- exec("echo 'hello' > file.txt")

如果参数过长导致错误，可以：
1. 拆分成多个小文件
2. 使用代码块格式（见文档）
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "文件编码，默认 utf-8",
                        "default": "utf-8"
                    },
                    "notify_frontend": {
                        "type": "boolean",
                        "description": "是否通知前端显示此文件，默认 False（中间文件不显示）",
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
            "description": """执行一次性命令（非持久化）。
            
支持的命令：
- Bash 命令：ls -la, cat file.txt, grep pattern file
- Python 短代码：python -c "print('hello')"
- Python 脚本：python script.py

执行策略：
- 短命令（1 行）：直接执行
- 长代码：先用 write_file 创建脚本，再执行

后台运行：
- 对于长时间任务（> 30s），使用 background=True
- 后台任务返回 session_id，可通过 process 工具查询

⚠️ 重要：每次 exec 都是新进程，变量不会保持！
如需多步执行和变量持久化，使用 shell_exec。

示例：
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
                        "description": "要执行的命令"
                    },
                    "workdir": {
                        "type": "string",
                        "description": "工作目录（可选，默认为用户脚本目录）"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒），默认 300",
                        "default": 300
                    },
                    "background": {
                        "type": "boolean",
                        "description": "是否后台运行，默认 False",
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
            "description": """编辑文件（字符串替换）。
            
适用场景：
- 修改代码中的特定行
- 更正配置文件中的值
- 批量替换内容

使用建议：
- old_string 必须完全匹配（包括空格、缩进）
- 建议先用 read_file 确认内容
- 替换失败时会提示相似的行

示例：
edit_file("config.py", "DEBUG = False", "DEBUG = True")
edit_file("script.py", "old_func()", "new_func()", replace_all=True)
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "要替换的字符串（必须完全匹配）"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "替换后的字符串"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "是否替换所有匹配，默认 False（只替换第一个）",
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
            "description": """搜索文件内容（支持正则表达式）。
            
适用场景：
- 查找代码中的函数定义
- 搜索配置文件中的关键字
- 定位错误信息位置

示例：
grep("def.*main", "script.py")  # 查找 main 函数
grep("ERROR", "app.log", case_insensitive=True)
grep("import.*pandas", ".", recursive=True)  # 递归搜索
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索模式（支持正则表达式）"
                    },
                    "path": {
                        "type": "string",
                        "description": "文件或目录路径"
                    },
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "忽略大小写，默认 False",
                        "default": False
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "递归搜索目录，默认 False",
                        "default": False
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "显示上下文行数，默认 0",
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
            "description": """查找文件（按文件名）。
            
适用场景：
- 查找特定类型的文件（*.py, *.csv）
- 定位配置文件
- 浏览项目结构

示例：
find("*.py")  # 查找所有 Python 文件
find("config.*")  # 查找所有 config 文件
find("*test*", "src/")  # 在 src 目录下查找
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "文件名模式（支持 glob，如 *.py）"
                    },
                    "directory": {
                        "type": "string",
                        "description": "搜索目录，默认当前目录",
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
            "description": """列出目录内容。
            
⚠️ 重要：默认只显示10个文件，避免爆上下文！

适用场景：
- 快速查看少量文件
- 配合 pattern 参数精确过滤

必须使用pattern过滤：
- ls(pattern="*.pdf")  # 只看PDF文件
- ls(pattern="*.py", limit=20)  # 前20个Python文件
- find("*.csv")  # 或使用find工具

❌ 不要直接 ls() - 会返回10个文件，可能不是你要的！
✅ 使用 ls(pattern="...")  或 find() 精确查找

示例：
- ls(pattern="*.pdf")  # 查看PDF文件
- ls(pattern="test_*", limit=5)  # 前5个test开头的文件
- find("*.csv")  # 更好的选择
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径，默认当前目录",
                        "default": "."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "递归列出子目录，默认 False",
                        "default": False
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "显示隐藏文件，默认 False",
                        "default": False
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最多返回的条目数，默认 10（避免爆上下文）",
                        "default": 10
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件名过滤模式（支持通配符，如 '*.pdf', 'test_*'），强烈建议使用"
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
            "description": """管理后台运行的进程。
            
操作类型：
- list: 列出所有后台进程
- status: 查询指定进程的状态
- logs: 获取进程的输出日志
- kill: 终止指定进程

示例：
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
                        "description": "操作类型"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "进程会话 ID（list 操作不需要）"
                    }
                },
                "required": ["action"]
            }
        }
    }
]


# ============================================================================
# Tool Handlers - 导入所有工具实现
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
# 导出所有内容
# ============================================================================

__all__ = [
    # Context and Schemas
    "AgentContext",
    "TOOL_SCHEMAS",
    "TOOL_HANDLERS",
    
    # 安全
    "validate_path",
    "validate_command",
    "get_user_workdir",
    
    # 文件操作
    "read_file",
    "write_file",
    "edit_file",
    
    # 执行
    "exec_command",
    "process_manage",
    
    # 持久化会话
    "shell_exec",
    "shell_session_manage",
    
    # 辅助工具
    "grep",
    "find",
    "ls",
]
