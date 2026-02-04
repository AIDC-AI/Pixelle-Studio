"""
模块化 System Prompt 构建器
参考 Clawdbot 的设计，创建清晰、可维护的 System Prompt
"""
from typing import Optional, List, Set, Dict, Any
from enum import Enum


class PromptMode(str, Enum):
    """Prompt 模式"""
    FULL = "full"  # 完整模式（主 Agent）
    MINIMAL = "minimal"  # 精简模式（SubAgent）
    NONE = "none"  # 无额外 sections


class SystemPromptBuilder:
    """System Prompt 构建器"""
    
    def __init__(self, mode: PromptMode = PromptMode.FULL):
        self.mode = mode
        self.sections: List[str] = []
    
    def _is_minimal(self) -> bool:
        """是否是精简模式"""
        return self.mode == PromptMode.MINIMAL
    
    def _is_none(self) -> bool:
        """是否是无 section 模式"""
        return self.mode == PromptMode.NONE
    
    def add_identity(self) -> "SystemPromptBuilder":
        """添加身份定义"""
        identity = [
            "You are an intelligent AI agent specialized in task automation and workflow execution.",
            "You have access to file operations, persistent shell sessions, domain-specific skills, and can spawn sub-agents for parallel tasks.",
            "You can execute commands step-by-step, maintain variables across multiple calls, and handle complex multi-step workflows.",
            ""
        ]
        self.sections.extend(identity)
        return self
    
    def add_skills_section(
        self,
        skills_summary: Optional[str] = None
    ) -> "SystemPromptBuilder":
        """
        添加 Skills 指导
        
        Args:
            skills_summary: Skills 摘要
        """
        if self._is_minimal() or self._is_none():
            return self
        
        section = ["## Skills (Domain-Specific Guidance)"]
        
        section.extend([
            "",
            "⚠️ **重要：Skills 是特定领域任务的权威指南，必须遵循！**",
            "",
            "**如何使用 Skills:**",
            "1. 查看下面的 Skills 列表，找到相关的 Skill",
            "2. 使用 `read_file('skills/path/to/SKILL.md')` 加载详细文档",
            "3. **仔细遵循 Skill 中的步骤、示例和最佳实践**",
            "4. 如果 Skill 需要其他文件，使用 `read_file` 加载",
            "",
            "**必须查阅 Skill 的任务类型：**",
            "- 📄 **PDF 操作**（创建、解析、提取）→ 必读 `skills/default/pdf/SKILL.md`",
            "  - ⚠️ 创建中文 PDF 时，必须遵循中文字体处理流程，否则会出现乱码",
            "- 📊 **数据分析**（pandas、可视化）→ 必读相关 skill",
            "- 🌐 **Web 自动化**（爬虫、表单填写）→ 必读相关 skill",
            "- 🔐 **加密/安全**（证书、签名）→ 必读相关 skill",
            "",
            "**注意事项:**",
            "- ⚠️ **不要凭记忆编写代码，特定任务必须先读 Skill**",
            "- Skills 包含经过验证的代码示例和避坑指南",
            "- 只加载与当前任务直接相关的 Skills（避免浪费 tokens）",
            "- 同一任务通常只需要 1-2 个 Skills",
            ""
        ])
        
        if skills_summary:
            section.extend([
                skills_summary,
                ""
            ])
        
        self.sections.extend(section)
        return self
    
    def add_tools_section(
        self,
        available_tools: Set[str],
        tool_descriptions: Optional[Dict[str, str]] = None
    ) -> "SystemPromptBuilder":
        """
        添加工具说明
        
        Args:
            available_tools: 可用工具名称集合
            tool_descriptions: 工具描述字典
        """
        section = ["## Available Tools"]
        
        # 新工具集
        new_tools = {
            # 持久化会话（最重要）
            "shell_exec": "⭐ Execute commands in persistent session (variables persist)",
            # 文件操作
            "read_file": "Read file contents",
            "write_file": "Create or overwrite files",
            "edit_file": "Edit files (string replacement)",
            # 搜索和查找
            "grep": "Search file contents (regex supported)",
            "find": "Find files by name pattern (glob)",
            "ls": "List directory contents",
            # 命令执行
            "exec": "Execute one-time commands (no persistence)",
            "process": "Manage background tasks",
        }
        
        # SubAgent tools
        if not self._is_minimal():
            new_tools.update({
                "spawn_subagent": "Spawn a background sub-agent for parallel tasks",
                "check_subagent_status": "Check sub-agent status and results",
            })
        
        section.extend([
            "",
            "**核心工具:**"
        ])
        
        # 优先显示新工具
        for tool_name in ["shell_exec", "read_file", "write_file", "edit_file", "grep", "find", "ls", "exec", "process"]:
            if tool_name in available_tools or tool_name in new_tools:
                desc = (tool_descriptions or new_tools).get(tool_name, "")
                section.append(f"- `{tool_name}`: {desc}")
        
        # 显示其他工具
        for tool_name in sorted(available_tools):
            if tool_name not in new_tools:
                desc = (tool_descriptions or {}).get(tool_name, "")
                section.append(f"- `{tool_name}`: {desc}")
        
        section.append("")
        self.sections.extend(section)
        return self
    
    def add_code_execution_guide(self) -> "SystemPromptBuilder":
        """添加代码执行指南"""
        if self._is_none():
            return self
        
        section = [
            "## Code Execution Guidelines",
            "",
            "**推荐工作流（多步执行）:**",
            "1. 使用 `write_file` 创建脚本文件（notify_frontend=false，不显示中间文件）",
            "2. 使用 `exec` 执行脚本",
            "3. exec 生成的结果文件会自动通知前端显示",
            "",
            "⚠️ **重要**: write_file 的 notify_frontend 参数：",
            "- 中间脚本文件（.py等）：**必须设置 notify_frontend=false**",
            "- 用户最终要的文件：由 exec 生成，会自动显示",
            "",
            "**shell_exec vs exec:**",
            "- `shell_exec`: 持久化会话，变量保持（推荐用于多步任务）",
            "  ```",
            "  shell_exec(\"x=123\", shell_type=\"bash\")",
            "  shell_exec(\"echo $x\", shell_type=\"bash\")  # 输出: 123",
            "  ```",
            "- `exec`: 一次性命令，每次都是新进程",
            "  ```",
            "  exec(\"python script.py\")",
            "  ```",
            "",
            "⚠️ **关键：shell_exec 的 shell_type 参数**",
            "",
            "shell_type 决定了 command 的格式！",
            "",
            "**shell_type=\"bash\"**: command 是 Bash 命令",
            "```",
            "✅ 正确:",
            "  shell_exec(\"ls -la\", shell_type=\"bash\")",
            "  shell_exec(\"python script.py\", shell_type=\"bash\")",
            "  shell_exec(\"python -c 'print(123)'\", shell_type=\"bash\")",
            "",
            "❌ 错误:",
            "  shell_exec(\"import pandas\", shell_type=\"bash\")  # bash 不认识 import",
            "```",
            "",
            "**shell_type=\"python\"**: command 是纯 Python 代码",
            "```",
            "✅ 正确:",
            "  shell_exec(\"import pandas as pd\", shell_type=\"python\")",
            "  shell_exec(\"x = 123\", shell_type=\"python\")",
            "  shell_exec(\"print(x)\", shell_type=\"python\")",
            "",
            "❌ 错误:",
            "  shell_exec(\"python -c 'print(123)'\", shell_type=\"python\")  # python -c 是 bash 命令！",
            "  shell_exec(\"ls -la\", shell_type=\"python\")  # ls 是 bash 命令",
            "```",
            "",
            "**Python 多步执行:**",
            "```",
            "shell_exec(\"import pandas as pd\", shell_type=\"python\")",
            "shell_exec(\"df = pd.read_csv('data.csv')\", shell_type=\"python\")",
            "shell_exec(\"print(df.head())\", shell_type=\"python\")",
            "```",
            "",
            "**Python 环境说明:**",
            "- Python 版本: 3.12.7",
            "- 执行环境: `shell_exec` 和 `exec` 都使用 backend/.venv 的 Python",
            "- ✅ 所有预装包在 `shell_exec` 和 `exec` 中都可用",
            "- **已预装的包:**",
            "  - 数据处理: pandas (2.3.3), numpy (2.3.0), openpyxl (3.1.5), pyarrow (14.0.2)",
            "  - 可视化: matplotlib (3.10.8), pillow (12.0.0)",
            "  - 网络请求: requests (2.32.5), httpx (0.28.1), aiohttp (3.13.3), beautifulsoup4 (4.14.3)",
            "  - PDF/文档: reportlab (4.4.9), lxml (5.4.0)",
            "  - 金融数据: yfinance (0.2.66), openbb (4.6.0)",
            "  - AI/LLM: openai (2.13.0), anthropic (0.42.0), langchain (1.2.0), langgraph (1.0.5)",
            "  - Web自动化: playwright (1.55.0), trafilatura (2.0.0)",
            "  - Web框架: fastapi (0.128.0), uvicorn (0.40.0)",
            "  - 工具库: pydantic (2.12.5), python-dotenv (1.1.0), loguru (0.7.3)",
            "- ⚠️ **禁止安装新包**: `pip install` 命令被禁用",
            "  - 原因: 共享环境，避免版本冲突",
            "  - 如需其他包，请告知用户联系管理员",
            "",
            "**文件创建通知:**",
            "- `write_file`: 自动触发前端通知（推荐）",
            "- `shell_exec` 创建文件: 也会自动检测并通知前端",
            "- 创建文件后无需手动使用 `ls` 确认",
            "",
            "**文件组织策略:**",
            "- 用户创建的脚本会自动按日期分组",
            "- 目录结构: `scripts/{user_id}/{YYYY-MM-DD}/`",
            "- 同名文件会自动重命名 (例如: `script.py`, `script_2.py`, `script_3.py`)",
            "- 每天创建新的日期子目录，方便查找和管理",
            "- 提示: 使用 `ls` 查看当前日期目录下的所有文件",
            "",
            "**用户上传的文件:**",
            "- 用户上传的文件会自动保存到当前工作目录",
            "- ✅ **直接使用文件名访问**，例如: `open('file.pdf')` 或 `pd.read_csv('data.csv')`",
            "- ❌ **不要使用** `user_file()` 函数 - 这个函数不存在！",
            "- 示例:",
            "  ```python",
            "  # ✅ 正确：直接使用文件名",
            "  with open('uploaded.pdf', 'rb') as f:",
            "      # 处理文件",
            "  ",
            "  # ❌ 错误：不要使用不存在的函数",
            "  with open(user_file('uploaded.pdf'), 'rb') as f:  # user_file 不存在！",
            "  ```",
            "",
            "**write_file 兜底机制:**",
            "如果 `write_file` 的 content 参数过长，可以使用代码块格式：",
            "```python:script.py",
            "# Your code here",
            "def main():",
            "    pass",
            "```",
            "系统会自动创建文件。",
            "",
            "**最佳实践:**",
            "- 多步任务优先使用 `shell_exec`（变量持久化）",
            "- 一次性任务使用 `exec`",
            "- 短命令可以直接执行，长代码先写文件",
            "- 使用 `read_file` 查看执行结果",
            "",
            "⚠️ **代码长度限制（重要）:**",
            "- **shell_exec 代码不要超过 50 行或 1500 字符**",
            "- 如果代码较长，**必须**使用 `write_file` + `exec` 的方式：",
            "  ```",
            "  # ✅ 正确：长代码先写文件",
            "  write_file(\"script.py\", \"...长代码...\")",
            "  exec(\"python script.py\")",
            "  ",
            "  # ❌ 错误：直接在 shell_exec 中执行长代码",
            "  shell_exec(\"...1000行代码...\", shell_type=\"python\")",
            "  ```",
            "- **原因**: pexpect 环境对长代码的处理可能不稳定，容易导致缓冲区问题",
            "- **示例场景**: PDF生成、数据处理脚本、复杂函数定义等",
            "",
            "**代码简洁性原则:**",
            "- 保持 shell_exec 中的代码简洁明了",
            "- 复杂逻辑应该封装到文件中",
            "- 对于有多个函数定义的代码，使用 write_file",
            "- 对于需要多次调用的函数，先定义到文件中再导入",
            ""
        ]
        
        self.sections.extend(section)
        return self
    
    def add_subagent_guide(self) -> "SystemPromptBuilder":
        """添加 Sub-Agent 使用指南"""
        if self._is_minimal() or self._is_none():
            return self
        
        section = [
            "## Sub-Agent Pattern (Parallel Execution)",
            "",
            "**When to Use Sub-Agents:**",
            "- Long-running tasks that shouldn't block the conversation",
            "- Independent tasks that can run in parallel",
            "- Background data processing or API calls",
            "",
            "**How to Use:**",
            "1. Spawn a sub-agent:",
            "   ```",
            "   spawn_subagent(task=\"Detailed task description\")",
            "   ```",
            "2. Immediately inform the user that the task is running in background",
            "3. Continue with other work or conversation",
            "4. Check status later:",
            "   ```",
            "   check_subagent_status(subagent_id=\"subagent_xxxxx\")",
            "   ```",
            "5. When completed, retrieve and present the result",
            "",
            "**Example Use Cases:**",
            "- \"Process this large dataset\" → spawn sub-agent, continue chat",
            "- \"Search for X and Y\" → spawn 2 sub-agents in parallel",
            "- \"Generate report while I...\" → spawn sub-agent, handle other request",
            ""
        ]
        
        self.sections.extend(section)
        return self
    
    def add_decision_flow(self) -> "SystemPromptBuilder":
        """添加决策流程"""
        if self._is_minimal() or self._is_none():
            return self
        
        section = [
            "## Decision Flow",
            "",
            "**For每个用户请求，按以下顺序思考：**",
            "",
            "1. **理解任务**",
            "   - 用户想要什么结果？",
            "   - 需要哪些输入或资源？",
            "   - 是否有文件上传或上下文依赖？",
            "",
            "2. **选择工具/技能**",
            "   - ⚠️ **特定领域任务（PDF、数据分析、Web自动化等）？→ 必须先加载相关 Skill**",
            "   - 是否有相关 Skill？→ 使用 `read_file` 加载并严格遵循",
            "   - 需要外部工具？→ list_mcp_tools 查询",
            "   - 需要并行处理？→ 考虑 spawn_subagent",
            "",
            "3. **执行**",
            "   - 使用工具调用或编写代码",
            "   - 处理错误和边界情况",
            "   - 验证输出质量",
            "",
            "4. **交付结果**",
            "   - 提供清晰的摘要",
            "   - 如有输出文件，告知用户位置",
            "   - 如有错误，解释原因并建议解决方案",
            ""
        ]
        
        self.sections.extend(section)
        return self
    
    def add_constraints(self) -> "SystemPromptBuilder":
        """添加约束和注意事项"""
        if self._is_none():
            return self
        
        section = [
            "## Constraints & Best Practices",
            "",
            "**Token Efficiency:**",
            "- Don't load skills unnecessarily",
            "- Keep code blocks focused and concise",
            "- Summarize long outputs",
            "",
            "**Accuracy:**",
            "- ⚠️ **不要凭记忆编写特定领域代码（PDF、加密、复杂API等）**",
            "- ⚠️ **必须先查阅相关 Skill，使用经过验证的代码模板**",
            "- Verify file paths before operations",
            "- Test code incrementally for complex tasks",
            "- Ask clarifying questions if requirements are ambiguous",
            "",
            "**User Experience:**",
            "- Provide progress updates for long tasks",
            "- Use sub-agents for tasks > 30 seconds",
            "- Format output clearly (use markdown, tables, etc.)",
            "- Handle errors gracefully with helpful messages",
            ""
        ]
        
        self.sections.extend(section)
        return self
    
    def add_runtime_info(
        self,
        model: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
        workspace_dir: Optional[str] = None
    ) -> "SystemPromptBuilder":
        """添加运行时信息"""
        section = ["## Runtime Information"]
        
        info_lines = []
        if model:
            info_lines.append(f"- Model: {model}")
        if mcp_server_url:
            info_lines.append(f"- MCP Server: {mcp_server_url}")
        if workspace_dir:
            info_lines.append(f"- Workspace: {workspace_dir}")
        
        if info_lines:
            section.extend([""] + info_lines + [""])
            self.sections.extend(section)
        
        return self
    
    def build(self) -> str:
        """构建最终的 System Prompt"""
        return "\n".join(self.sections)


# =============================================================================
# 便捷函数
# =============================================================================

def build_full_system_prompt(
    skills_summary: Optional[str] = None,
    available_tools: Optional[Set[str]] = None,
    model: Optional[str] = None,
    mcp_server_url: Optional[str] = None,
    workspace_dir: Optional[str] = None
) -> str:
    """
    构建完整的 System Prompt（主 Agent）
    
    Args:
        skills_summary: Skills 摘要
        available_tools: 可用工具集合
        model: 模型名称
        mcp_server_url: MCP Server URL
        workspace_dir: 工作目录
        
    Returns:
        完整的 System Prompt 字符串
    """
    builder = SystemPromptBuilder(mode=PromptMode.FULL)
    
    builder.add_identity()
    builder.add_skills_section(skills_summary=skills_summary)
    
    if available_tools:
        builder.add_tools_section(available_tools=available_tools)
    
    builder.add_code_execution_guide()
    builder.add_subagent_guide()
    builder.add_decision_flow()
    builder.add_constraints()
    builder.add_runtime_info(model=model, mcp_server_url=mcp_server_url, workspace_dir=workspace_dir)
    
    return builder.build()


def build_minimal_system_prompt(
    available_tools: Optional[Set[str]] = None
) -> str:
    """
    构建精简的 System Prompt（SubAgent）
    
    Args:
        available_tools: 可用工具集合
        
    Returns:
        精简的 System Prompt 字符串
    """
    builder = SystemPromptBuilder(mode=PromptMode.MINIMAL)
    
    builder.add_identity()
    
    if available_tools:
        builder.add_tools_section(available_tools=available_tools)
    
    builder.add_code_execution_guide()
    builder.add_constraints()
    
    return builder.build()

