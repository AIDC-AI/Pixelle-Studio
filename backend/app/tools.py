"""
Tools for SkillAgent - Defined using OpenAI Agents SDK @function_tool decorator.

This module defines 5 tools:
1. load_skill - Load skill documentation (SKILL.md)
2. read_skill_file - Read a specific file from skill directory
3. list_skill_tree - List skill directory structure
4. execute_code - Execute Python code
5. list_mcp_tools - Discover available MCP tools
"""

import os
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from agents import function_tool, RunContextWrapper

from app.skills.loader import SkillLoader, get_skill_loader
from app.execution.runner import run_script
from app.utils.network import LOCAL_IP, SERVER_PORT

import logging
logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to all tools during agent execution."""
    user_id: Optional[str] = None
    session_id: str = ""
    skill_loader: SkillLoader = field(default_factory=get_skill_loader)
    script_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "scripts" / "default")
    backend_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    mcp_server_url: Optional[str] = None
    mcp_server_type: str = "sse"
    loaded_skills: Dict[str, str] = field(default_factory=dict)
    tool_call_count: int = 0
    pending_code_queue: List[str] = field(default_factory=list)  # Queue for <execute> blocks
    
    def __post_init__(self):
        """Ensure script_dir exists."""
        self.script_dir.mkdir(parents=True, exist_ok=True)


@function_tool
async def load_skill(ctx: RunContextWrapper[AgentContext], skill_name: str) -> str:
    """
    Load skill documentation (SKILL.md) for domain-specific guidance.
    
    Use this tool when you need detailed instructions for a specific task domain.
    
    Args:
        skill_name: Name of the skill to load (e.g., "xlsx", "pptx", "video")
    
    Returns:
        The full content of the skill's SKILL.md documentation, or an error message if not found.
    """
    context = ctx.context
    user_id = context.user_id
    skill_loader = context.skill_loader
    
    logger.info(f"[Tool] Loading skill: {skill_name}")
    
    skill_content = skill_loader.read_skill(skill_name, user_id)
    
    if skill_content:
        # Store in loaded_skills for reference
        context.loaded_skills[skill_name] = skill_content
        
        # Find referenced documents in SKILL.md
        links = skill_loader.parse_skill_links(skill_name, user_id)
        referenced_docs = [link.path for link in links if link.exists and link.path.endswith('.md')]
        
        # 返回结构化 JSON，包含 skill_name 便于前端识别
        result = {
            "__tool__": "load_skill",  # 标识工具类型
            "skill_name": skill_name,
            "content": skill_content,
            "referenced_docs": referenced_docs[:5] if referenced_docs else [],
            "status": "success"
        }
        
        return json.dumps(result, ensure_ascii=False)
    else:
        return json.dumps({
            "__tool__": "load_skill",
            "skill_name": skill_name,
            "status": "error",
            "error": f"Skill '{skill_name}' not found. Please check the skill name or try a different approach."
        }, ensure_ascii=False)


@function_tool
async def read_skill_file(ctx: RunContextWrapper[AgentContext], skill_name: str, file_path: str) -> str:
    """
    Read a specific file from a skill's directory.
    
    Use this to access detailed documentation, helper scripts, templates,
    or configuration files within a skill directory.
    
    Args:
        skill_name: Name of the skill (e.g., "xlsx", "pptx")
        file_path: Relative path to the file within the skill directory (e.g., "html2pptx.md", "scripts/helper.py")
    
    Returns:
        The file content as a string, or an error message if not found/readable.
    """
    context = ctx.context
    user_id = context.user_id
    skill_loader = context.skill_loader
    
    logger.info(f"[Tool] Reading skill file: {skill_name}/{file_path}")
    
    file_content = skill_loader.read_skill_file(skill_name, file_path, user_id)
    
    if file_content:
        return f"# Content of '{skill_name}/{file_path}'\n\n```\n{file_content}\n```"
    else:
        return f"File '{skill_name}/{file_path}' not found or not readable. Please check the path or use `list_skill_tree` to see available files."


@function_tool
async def list_skill_tree(ctx: RunContextWrapper[AgentContext], skill_name: str) -> str:
    """
    List the directory structure of a skill.
    
    Use this to discover what files are available in a skill directory,
    such as documentation files, scripts, templates, or resources.
    
    Args:
        skill_name: Name of the skill (e.g., "xlsx", "pptx")
    
    Returns:
        A JSON representation of the directory tree, or an error message if skill not found.
    """
    context = ctx.context
    user_id = context.user_id
    skill_loader = context.skill_loader
    
    logger.info(f"[Tool] Listing skill tree: {skill_name}")
    
    tree = skill_loader.list_skill_tree(skill_name, user_id)
    
    if tree:
        tree_json = json.dumps(tree, indent=2, ensure_ascii=False)
        return f"# Directory structure of skill '{skill_name}'\n\n```json\n{tree_json}\n```\n\nYou can use `read_skill_file` to read specific files."
    else:
        return f"Skill '{skill_name}' not found. Please check the skill name."


@function_tool
async def execute_code(ctx: RunContextWrapper[AgentContext], code: Optional[str] = None) -> str:
    """
    ⚠️ CRITICAL TOOL - Execute Python code to generate files and produce results.
    
    Args:
        code: Python code to execute (optional, will use queue if not provided)
    
    Returns:
        Execution results including stdout, stderr, parsed JSON result, and generated file URLs.
    """
    context = ctx.context
    context.tool_call_count += 1
    
    # Determine code source: direct parameter or queue
    code_to_execute = None
    code_source = None
    
    # Filter out invalid code values (e.g., LLM sometimes sends "None" string instead of null)
    # A valid code should be non-empty and not just "None" or whitespace
    valid_code = (
        code is not None 
        and code.strip() 
        and code.strip().lower() != "none"  # Filter out "None" string from LLM
    )
    
    if valid_code:
        # Method 1: Code passed as parameter (direct)
        code_to_execute = code.strip()
        code_source = "parameter"
        logger.info(f"[Tool] execute_code called with code parameter (call #{context.tool_call_count}), length: {len(code_to_execute)} chars")
    else:
        # Code parameter is invalid (None, empty, or "None" string)
        if code is not None and code.strip():
            # LLM sent invalid code like "None" - log warning
            logger.warning(f"[Tool] execute_code received invalid code parameter: {repr(code)}, falling back to queue")
        
        if context.pending_code_queue:
            # Method 2: Code from queue (legacy)
            code_to_execute = context.pending_code_queue.pop()
            code_source = "queue"
            logger.info(f"[Tool] execute_code using code from queue (call #{context.tool_call_count}), length: {len(code_to_execute)} chars, remaining: {len(context.pending_code_queue)}")
        else:
            # No code available
            logger.warning(f"[Tool] execute_code called but no code provided (call #{context.tool_call_count})")
            return """## No Code Found

You called execute_code() but didn't provide any code.
"""
    
    code = code_to_execute
    logger.info(f"[Tool] Executing code from {code_source}")
    
    # Build skill helpers injection code
    skill_helpers_code = _build_skill_helpers_code(context)
    
    # Wrap code with proper structure
    wrapped_code = f'''import sys
import json
import os
import subprocess
from pathlib import Path
{skill_helpers_code}
{code}
'''
    
    # Save script to scripts/ directory
    script_name = f"{context.session_id}_{context.tool_call_count:02d}_{uuid.uuid4().hex[:6]}.py"
    script_file = context.script_dir / script_name
    script_file.write_text(wrapped_code)
    
    # Execute and collect output
    output_lines = []
    error_lines = []
    result = None
    status = "success"
    
    try:
        async for log in run_script(str(script_file), cwd=str(context.backend_root)):
            if log.get("stream") == "stdout":
                content = log.get("content", "")
                output_lines.append(content)
                # Try to parse JSON result
                if content.strip().startswith("{"):
                    try:
                        result = json.loads(content.strip())
                    except:
                        pass
            elif log.get("stream") == "stderr":
                error_lines.append(log.get("content", ""))
            elif log.get("type") == "result":
                if log.get("status") != "success":
                    status = "error"
    except Exception as e:
        status = "error"
        error_lines.append(str(e))
    
    # Check for output files and generate URLs
    output_files = []
    if result and isinstance(result, dict):
        output_file_names = result.get("output_file_names", [])
        if output_file_names:
            for file_name in output_file_names:
                file_path = context.script_dir / file_name
                if file_path.exists():
                    path_prefix = f"{context.user_id}/" if context.user_id else "default/"
                    file_url = f"http://{LOCAL_IP}:{SERVER_PORT}/f/{path_prefix}{file_name}"
                    output_files.append({
                        "file_name": file_name,
                        "file_url": file_url,
                        "file_size": file_path.stat().st_size
                    })
    
    # Build structured result (返回结构化 JSON，不用正则解析)
    exec_result = {
        "__tool__": "execute_code",  # 标识工具类型，便于 agent 识别
        "status": status,
        "stdout": "\n".join(output_lines),
        "stderr": "\n".join(error_lines),
        "result": result,
        "script_path": str(script_file),
        "output_files": output_files
    }
    
    # 返回 JSON 字符串，LLM 可以理解，agent 可以直接解析
    return json.dumps(exec_result, ensure_ascii=False)


@function_tool
async def list_mcp_tools(ctx: RunContextWrapper[AgentContext]) -> str:
    """
    Discover all available MCP tools from registered servers.
    
    Use this tool when you need external services (image generation, audio synthesis, etc.)
    but no skill matches the task. This returns a list of available MCP tools with their
    names, descriptions, and input schemas.
    
    Returns:
        A JSON list of available tools with name, description, and input_schema.
    """
    from app.mcp_client import list_mcp_tools as mcp_list_tools, register_tool_server, _TOOL_SERVER_MAP
    
    context = ctx.context
    
    logger.info("[Tool] Listing MCP tools")
    
    # Ensure default server is registered if configured
    if context.mcp_server_url and not _TOOL_SERVER_MAP:
        register_tool_server("__default__", context.mcp_server_url, context.mcp_server_type)
    
    try:
        tools = await mcp_list_tools()
        
        if not tools:
            return "No MCP tools available. No MCP servers are registered."
        
        # Format tools list
        result = f"# Available MCP Tools ({len(tools)} total)\n\n"
        
        for tool in tools:
            result += f"## {tool['name']}\n"
            result += f"**Description**: {tool.get('description', 'No description')}\n"
            if tool.get('input_schema'):
                result += f"**Input Schema**:\n```json\n{json.dumps(tool['input_schema'], indent=2)}\n```\n"
            result += "\n"
        
        result += "\nUse `execute_code` with `await call_tool('tool_name', {...})` to call these tools."
        
        return result
        
    except Exception as e:
        logger.error(f"[Tool] Error listing MCP tools: {e}")
        return f"Error listing MCP tools: {str(e)}"


def _build_skill_helpers_code(context: AgentContext) -> str:
    """
    Build the skill_helpers module code to inject into execution environment.
    
    All paths are RELATIVE to the execution cwd (backend root).
    Provides:
    - skill_path() for skill resources, user_file() for user files
    - call_tool() for MCP tool calling (async)
    """
    # Build MCP server registration if configured
    mcp_setup = ""
    if context.mcp_server_url:
        mcp_setup = f'''
# Register default MCP server for all tools
_DEFAULT_MCP_SERVER = "{context.mcp_server_url}"
_DEFAULT_MCP_TYPE = "{context.mcp_server_type}"

# Pre-register a placeholder to ensure list_mcp_tools can discover the server
from app.mcp_client import _TOOL_SERVER_MAP, register_tool_server
if not _TOOL_SERVER_MAP:
    register_tool_server("__default__", _DEFAULT_MCP_SERVER, _DEFAULT_MCP_TYPE)

# Wrap call_tool to use default server if tool not registered
_original_call_tool = call_tool
async def call_tool(tool_name: str, args: dict = None):
    if tool_name not in _TOOL_SERVER_MAP:
        register_tool_server(tool_name, _DEFAULT_MCP_SERVER, _DEFAULT_MCP_TYPE)
    return await _original_call_tool(tool_name, args)
'''
    
    # Get skill paths map for current user (uses cache, no rescan)
    skills = context.skill_loader.scan_skills(context.user_id)  # Uses cached skills
    skill_paths_map = {s.name: s.directory for s in skills}
    
    script_subdir = context.user_id if context.user_id else "default"
    
    return f'''
# === Skill Helpers (auto-injected) ===
# Working directory is backend root, containing: skills/ and scripts/

import os
import json

# Map of skill name to its actual path (default vs user)
_SKILL_PATHS = {json.dumps(skill_paths_map)}
SCRIPTS_ROOT = "scripts/{script_subdir}"

def skill_path(skill_name: str, *parts) -> str:
    """Get relative path: skills/<source>/<skill_name>/[parts...]"""
    base_path = _SKILL_PATHS.get(skill_name)
    if not base_path:
        # Fallback (should not happen if skill is loaded)
        return os.path.join("skills", "default", skill_name, *parts)
    return os.path.join(base_path, *parts)

def user_file(*parts) -> str:
    """Get path to user's working files: scripts/<user_id>/[parts...]
    
    Use this for: user uploaded files, generated outputs, temporary files.
    NOT for skill resources - use skill_path() for those.
    """
    return os.path.join(SCRIPTS_ROOT, *parts)

# MCP Tool Calling Support
import sys
sys.path.insert(0, '.')
from app.mcp_client import call_tool, list_mcp_tools
{mcp_setup}
# === End Skill Helpers ===
'''


# Export all tools for use in agent
SKILL_TOOLS = [
    load_skill,
    read_skill_file,
    list_skill_tree,
    execute_code,
    list_mcp_tools,
]
