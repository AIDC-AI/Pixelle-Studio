"""
Modular System Prompt Builder
Reference: Clawdbot design pattern for clear, maintainable System Prompts.
"""
from typing import Optional, List, Set, Dict, Any
from enum import Enum


class PromptMode(str, Enum):
    """Prompt mode"""
    FULL = "full"  # Full mode (main Agent)
    MINIMAL = "minimal"  # Minimal mode (SubAgent)
    NONE = "none"  # No extra sections


class SystemPromptBuilder:
    """System Prompt Builder"""
    
    def __init__(self, mode: PromptMode = PromptMode.FULL):
        self.mode = mode
        self.sections: List[str] = []
    
    def _is_minimal(self) -> bool:
        """Check if in minimal mode"""
        return self.mode == PromptMode.MINIMAL
    
    def _is_none(self) -> bool:
        """Check if in no-section mode"""
        return self.mode == PromptMode.NONE
    
    def add_identity(self) -> "SystemPromptBuilder":
        """Add identity definition"""
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
        Add Skills guidance section.
        
        Args:
            skills_summary: Skills summary text
        """
        if self._is_minimal() or self._is_none():
            return self
        
        section = ["## Skills (Domain-Specific Guidance)"]
        
        section.extend([
            "",
            "**Important: Skills are authoritative guides for domain-specific tasks and must be followed!**",
            "",
            "**How to use Skills:**",
            "1. Review the Skills list below to find the relevant Skill",
            "2. Use `read_file('skills/path/to/SKILL.md')` to load detailed documentation",
            "3. **Carefully follow the steps, examples, and best practices in the Skill**",
            "4. If the Skill requires other files, load them with `read_file`",
            "",
            "**Task types that require consulting Skills:**",
            "- PDF operations (create, parse, extract) -> must read `skills/default/pdf/SKILL.md`",
            "  - When creating Chinese PDFs, you must follow the Chinese font handling workflow to avoid garbled text",
            "- Data analysis (pandas, visualization) -> must read related skill",
            "- Web automation (scraping, form filling) -> must read related skill",
            "- Encryption/security (certificates, signatures) -> must read related skill",
            "",
            "**Notes:**",
            "- **Do not write code from memory for domain-specific tasks - read the Skill first**",
            "- Skills contain verified code examples and troubleshooting guides",
            "- Only load Skills directly related to the current task (avoid wasting tokens)",
            "- A single task typically requires only 1-2 Skills",
            "- **When a Skill uses `call_tool()`, it is already pre-injected in the Python environment — just call it directly!**",
            "- **NEVER define your own `call_tool` function, mock, or wrapper — it breaks the real tool calls!**",
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
        Add tools description section.
        
        Args:
            available_tools: Set of available tool names
            tool_descriptions: Tool description dictionary
        """
        section = ["## Available Tools"]
        
        # New tool set
        new_tools = {
            # Persistent sessions (most important)
            "shell_exec": "Execute commands in persistent session (variables persist)",
            # File operations
            "read_file": "Read file contents",
            "write_file": "Create or overwrite files",
            "edit_file": "Edit files (string replacement)",
            # Search and find
            "grep": "Search file contents (regex supported)",
            "find": "Find files by name pattern (glob)",
            "ls": "List directory contents",
            # Command execution
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
            "**Core Tools:**"
        ])
        
        # Show new tools first
        for tool_name in ["shell_exec", "read_file", "write_file", "edit_file", "grep", "find", "ls", "exec", "process"]:
            if tool_name in available_tools or tool_name in new_tools:
                desc = (tool_descriptions or new_tools).get(tool_name, "")
                section.append(f"- `{tool_name}`: {desc}")
        
        # Show other tools
        for tool_name in sorted(available_tools):
            if tool_name not in new_tools:
                desc = (tool_descriptions or {}).get(tool_name, "")
                section.append(f"- `{tool_name}`: {desc}")
        
        section.append("")
        self.sections.extend(section)
        return self
    
    def add_code_execution_guide(self) -> "SystemPromptBuilder":
        """Add code execution guidelines"""
        if self._is_none():
            return self
        
        section = [
            "## Code Execution Guidelines",
            "",
            "**Recommended workflow (multi-step execution):**",
            "1. Use `write_file` to create script files (notify_frontend=false, hide intermediate files)",
            "2. Use `exec` to execute scripts",
            "3. Result files generated by exec will automatically notify the frontend",
            "",
            "**Important**: write_file's notify_frontend parameter:",
            "- Intermediate script files (.py, etc.): **must set notify_frontend=false**",
            "- Final files the user wants: generated by exec, displayed automatically",
            "",
            "**shell_exec vs exec:**",
            "- `shell_exec`: Persistent session, variables persist (recommended for multi-step tasks)",
            "  ```",
            "  shell_exec(\"x=123\", shell_type=\"bash\")",
            "  shell_exec(\"echo $x\", shell_type=\"bash\")  # Output: 123",
            "  ```",
            "- `exec`: One-time command, new process each time",
            "  ```",
            "  exec(\"python script.py\")",
            "  ```",
            "",
            "**Key: shell_exec's shell_type parameter**",
            "",
            "shell_type determines the command format!",
            "",
            "**shell_type=\"bash\"**: command is a Bash command",
            "```",
            "Correct:",
            "  shell_exec(\"ls -la\", shell_type=\"bash\")",
            "  shell_exec(\"python script.py\", shell_type=\"bash\")",
            "  shell_exec(\"python -c 'print(123)'\", shell_type=\"bash\")",
            "",
            "Wrong:",
            "  shell_exec(\"import pandas\", shell_type=\"bash\")  # bash doesn't recognize import",
            "```",
            "",
            "**shell_type=\"python\"**: command is pure Python code",
            "```",
            "Correct:",
            "  shell_exec(\"import pandas as pd\", shell_type=\"python\")",
            "  shell_exec(\"x = 123\", shell_type=\"python\")",
            "  shell_exec(\"print(x)\", shell_type=\"python\")",
            "",
            "Wrong:",
            "  shell_exec(\"python -c 'print(123)'\", shell_type=\"python\")  # python -c is a bash command!",
            "  shell_exec(\"ls -la\", shell_type=\"python\")  # ls is a bash command",
            "```",
            "",
            "**Python multi-step execution:**",
            "```",
            "shell_exec(\"import pandas as pd\", shell_type=\"python\")",
            "shell_exec(\"df = pd.read_csv('data.csv')\", shell_type=\"python\")",
            "shell_exec(\"print(df.head())\", shell_type=\"python\")",
            "```",
            "",
            "**Python environment:**",
            "- Python version: 3.12.7",
            "- Execution environment: both `shell_exec` and `exec` use backend/.venv Python",
            "- All pre-installed packages are available in `shell_exec` and `exec`",
            "- **Pre-installed packages:**",
            "  - Data processing: pandas (2.3.3), numpy (2.3.0), openpyxl (3.1.5), pyarrow (14.0.2)",
            "  - Visualization: matplotlib (3.10.8), pillow (12.0.0)",
            "  - Network requests: requests (2.32.5), httpx (0.28.1), aiohttp (3.13.3), beautifulsoup4 (4.14.3)",
            "  - PDF/documents: reportlab (4.4.9), lxml (5.4.0)",
            "  - Financial data: yfinance (0.2.66), openbb (4.6.0)",
            "  - AI/LLM: openai (2.13.0), anthropic (0.42.0), langchain (1.2.0), langgraph (1.0.5)",
            "  - Web automation: playwright (1.55.0), trafilatura (2.0.0)",
            "  - Web framework: fastapi (0.128.0), uvicorn (0.40.0)",
            "  - Utilities: pydantic (2.12.5), python-dotenv (1.1.0), loguru (0.7.3)",
            "- **Package installation is prohibited**: `pip install` command is disabled",
            "  - Reason: shared environment, avoid version conflicts",
            "  - If you need additional packages, ask the user to contact the admin",
            "",
            "**⚠️ call_tool() - Pre-injected MCP Tool Interface (CRITICAL):**",
            "- `call_tool(tool_name, args)` is **already pre-injected** into ALL Python/IPython execution environments",
            "- It is a synchronous function that calls external MCP tools (e.g. web_search_exa, fetch, company_research_exa, etc.)",
            "- **DO NOT define, mock, or redefine `call_tool` yourself** — it is already available!",
            "- **DO NOT import it** — it is already in the global namespace of the Python session",
            "- **DO NOT write subprocess/HTTP code to simulate tool calls** — just use `call_tool()` directly",
            "- Usage (in shell_exec with shell_type='python' or in scripts executed via exec):",
            "  ```python",
            "  # ✅ Correct: use call_tool directly (it's already available)",
            "  result = call_tool('web_search_exa', {'query': 'search term'})",
            "  print(result)",
            "  ",
            "  # ❌ WRONG: do NOT define your own call_tool!",
            "  # def call_tool(name, args):  # NEVER DO THIS",
            "  #     ...mock implementation...",
            "  ```",
            "- When a Skill instructs you to use `call_tool()`, just call it — it works immediately",
            "- The function handles server routing and tool discovery automatically",
            "",
            "**File creation notifications:**",
            "- `write_file`: automatically triggers frontend notification (recommended)",
            "- `shell_exec` file creation: also auto-detected and notifies frontend",
            "- No need to manually use `ls` to confirm after creating files",
            "",
            "**File organization strategy:**",
            "- User-created scripts are automatically grouped by date",
            "- Directory structure: `scripts/{user_id}/{YYYY-MM-DD}/`",
            "- Same-name files are auto-renamed (e.g.: `script.py`, `script_2.py`, `script_3.py`)",
            "- A new date subdirectory is created each day for easy lookup and management",
            "- Tip: use `ls` to view all files in the current date directory",
            "",
            "**User uploaded files:**",
            "- User uploaded files are automatically saved to the current working directory",
            "- **Use the filename directly**, e.g.: `open('file.pdf')` or `pd.read_csv('data.csv')`",
            "- **Do not use** `user_file()` function - this function does not exist!",
            "- Example:",
            "  ```python",
            "  # Correct: use filename directly",
            "  with open('uploaded.pdf', 'rb') as f:",
            "      # process file",
            "  ",
            "  # Wrong: do not use non-existent functions",
            "  with open(user_file('uploaded.pdf'), 'rb') as f:  # user_file doesn't exist!",
            "  ```",
            "",
            "**write_file fallback mechanism:**",
            "If `write_file`'s content parameter is too long, use code block format:",
            "```python:script.py",
            "# Your code here",
            "def main():",
            "    pass",
            "```",
            "The system will automatically create the file.",
            "",
            "**Best practices:**",
            "- For multi-step tasks, prefer `shell_exec` (variable persistence)",
            "- For one-time tasks, use `exec`",
            "- Short commands can be executed directly; write long code to files first",
            "- Use `read_file` to view execution results",
            "",
            "**Code length limit (important):**",
            "- **shell_exec code should not exceed 50 lines or 1500 characters**",
            "- For longer code, **must** use `write_file` + `exec`:",
            "  ```",
            "  # Correct: write long code to file first",
            "  write_file(\"script.py\", \"...long code...\")",
            "  exec(\"python script.py\")",
            "  ",
            "  # Wrong: execute long code directly in shell_exec",
            "  shell_exec(\"...1000 lines of code...\", shell_type=\"python\")",
            "  ```",
            "- **Reason**: pexpect environment may be unstable with long code, causing buffer issues",
            "- **Example scenarios**: PDF generation, data processing scripts, complex function definitions",
            "",
            "**Code conciseness principle:**",
            "- Keep shell_exec code concise and clear",
            "- Complex logic should be encapsulated in files",
            "- For code with multiple function definitions, use write_file",
            "- For functions that need to be called multiple times, define them in a file first then import",
            ""
        ]
        
        self.sections.extend(section)
        return self
    
    def add_subagent_guide(self) -> "SystemPromptBuilder":
        """Add Sub-Agent usage guide"""
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
            "- \"Process this large dataset\" -> spawn sub-agent, continue chat",
            "- \"Search for X and Y\" -> spawn 2 sub-agents in parallel",
            "- \"Generate report while I...\" -> spawn sub-agent, handle other request",
            ""
        ]
        
        self.sections.extend(section)
        return self
    
    def add_decision_flow(self) -> "SystemPromptBuilder":
        """Add decision flow"""
        if self._is_minimal() or self._is_none():
            return self
        
        section = [
            "## Decision Flow",
            "",
            "**For each user request, think through the following:**",
            "",
            "1. **Understand the task**",
            "   - What result does the user want?",
            "   - What inputs or resources are needed?",
            "   - Are there file uploads or context dependencies?",
            "",
            "2. **Choose tools/skills**",
            "   - Domain-specific task (PDF, data analysis, web automation, etc.)? -> **Must load the relevant Skill first**",
            "   - Is there a relevant Skill? -> Use `read_file` to load and follow strictly",
            "   - Need external tools? -> Use list_mcp_tools to query",
            "   - Need parallel processing? -> Consider spawn_subagent",
            "",
            "3. **Execute**",
            "   - Use tool calls or write code",
            "   - Handle errors and edge cases",
            "   - Validate output quality",
            "",
            "4. **Deliver results**",
            "   - Provide a clear summary",
            "   - If there are output files, inform the user of their location",
            "   - If there are errors, explain the cause and suggest solutions",
            ""
        ]
        
        self.sections.extend(section)
        return self
    
    def add_constraints(self) -> "SystemPromptBuilder":
        """Add constraints and best practices"""
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
            "- **Do not write domain-specific code from memory (PDF, encryption, complex APIs, etc.)**",
            "- **Must consult the relevant Skill and use verified code templates**",
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
        """Add runtime information"""
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
        """Build the final System Prompt"""
        return "\n".join(self.sections)


# =============================================================================
# Convenience functions
# =============================================================================

def build_full_system_prompt(
    skills_summary: Optional[str] = None,
    available_tools: Optional[Set[str]] = None,
    model: Optional[str] = None,
    mcp_server_url: Optional[str] = None,
    workspace_dir: Optional[str] = None
) -> str:
    """
    Build the complete System Prompt (main Agent).
    
    Args:
        skills_summary: Skills summary text
        available_tools: Set of available tools
        model: Model name
        mcp_server_url: MCP Server URL
        workspace_dir: Working directory
        
    Returns:
        Complete System Prompt string
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
    Build the minimal System Prompt (SubAgent).
    
    Args:
        available_tools: Set of available tools
        
    Returns:
        Minimal System Prompt string
    """
    builder = SystemPromptBuilder(mode=PromptMode.MINIMAL)
    
    builder.add_identity()
    
    if available_tools:
        builder.add_tools_section(available_tools=available_tools)
    
    builder.add_code_execution_guide()
    builder.add_constraints()
    
    return builder.build()
