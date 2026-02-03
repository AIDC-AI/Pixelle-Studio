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
            "You can load domain-specific skills, execute Python code, call external tools, and spawn sub-agents for parallel tasks.",
            ""
        ]
        self.sections.extend(identity)
        return self
    
    def add_skills_section(
        self,
        skills_summary: Optional[str] = None,
        progressive_loading: bool = True
    ) -> "SystemPromptBuilder":
        """
        添加 Skills 指导
        
        Args:
            skills_summary: Skills 摘要（按需加载时显示简短描述）
            progressive_loading: 是否使用渐进式加载（推荐）
        """
        if self._is_minimal() or self._is_none():
            return self
        
        section = ["## Skills (Domain-Specific Guidance)"]
        
        if progressive_loading:
            section.extend([
                "",
                "**Progressive Loading Strategy:**",
                "1. Scan the <available_skills> list below for skill descriptions",
                "2. If a skill clearly applies to the user's request:",
                "   - Call `load_skill(skill_name)` to get detailed guidance",
                "   - Follow the loaded skill's instructions carefully",
                "3. If multiple skills could apply: choose the most specific one",
                "4. If no skill clearly applies: proceed without loading any",
                "",
                "**Constraints:**",
                "- Never load more than 1-2 skills per request (avoid token waste)",
                "- Only load skills that are directly relevant to the current task",
                "- Skills contain step-by-step guides, examples, and best practices",
                ""
            ])
        
        if skills_summary:
            section.extend([
                "**Available Skills:**",
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
        
        # Core tools
        core_tools = {
            "load_skill": "Load domain-specific skill documentation",
            "read_skill_file": "Read a file from a skill directory",
            "list_skill_tree": "List skill directory structure",
            "list_mcp_tools": "Discover external MCP tools",
        }
        
        # SubAgent tools
        if not self._is_minimal():
            core_tools.update({
                "spawn_subagent": "Spawn a background sub-agent for parallel tasks",
                "check_subagent_status": "Check sub-agent status and results",
            })
        
        # Code execution (implicit)
        section.extend([
            "",
            "**Function Call Tools:**"
        ])
        for tool_name in sorted(available_tools):
            desc = (tool_descriptions or core_tools).get(tool_name, "")
            if desc:
                section.append(f"- `{tool_name}`: {desc}")
        
        section.extend([
            "",
            "**Code Execution (Implicit):**",
            "- Write Python code in <execute lang=\"python\">...</execute> blocks",
            "- Code is automatically executed in a sandboxed environment",
            "- Results are captured and returned to you",
            "- You can use libraries like pandas, openpyxl, requests, etc.",
            ""
        ])
        
        self.sections.extend(section)
        return self
    
    def add_code_execution_guide(self) -> "SystemPromptBuilder":
        """添加代码执行指南"""
        if self._is_none():
            return self
        
        section = [
            "## Code Execution Guidelines",
            "",
            "**Writing Executable Code:**",
            "1. Use <execute lang=\"python\">...</execute> blocks for Python code",
            "2. Always structure your output as a JSON dict in the final print:",
            "   ```python",
            "   import json",
            "   result = {\"status\": \"success\", \"data\": your_data}",
            "   print(json.dumps(result, ensure_ascii=False, indent=2))",
            "   ```",
            "3. For file operations: use absolute paths or paths relative to backend/scripts/",
            "4. Output files are automatically detected and returned to the user",
            "",
            "**Error Handling:**",
            "- Wrap risky code in try-except blocks",
            "- Return clear error messages in the JSON result",
            "- If code fails, analyze the error and retry with fixes",
            "",
            "**Best Practices:**",
            "- Keep code blocks focused (one task per block)",
            "- Add comments for complex logic",
            "- Use descriptive variable names",
            "- Test incrementally for complex workflows",
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
            "   - 是否有相关 Skill？→ 加载并遵循",
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
    builder.add_skills_section(skills_summary=skills_summary, progressive_loading=True)
    
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

