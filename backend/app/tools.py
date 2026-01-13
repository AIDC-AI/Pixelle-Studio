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
import socket
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from agents import function_tool, RunContextWrapper

from app.skills.loader import SkillLoader, get_skill_loader
from app.execution.runner import run_script

import logging
logger = logging.getLogger(__name__)


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


LOCAL_IP = get_local_ip()
SERVER_PORT = 8001  # Default backend port


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
    
    def __post_init__(self):
        """Ensure script_dir exists."""
        self.script_dir.mkdir(parents=True, exist_ok=True)


@function_tool
async def load_skill(ctx: RunContextWrapper[AgentContext], skill_name: str) -> str:
    """
    Load skill documentation (SKILL.md) for domain-specific guidance.
    
    Use this tool when you need detailed instructions for a specific task domain
    like Excel processing, PowerPoint creation, or video generation.
    
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
        
        result = f"# Skill '{skill_name}' Documentation\n\n{skill_content}"
        
        if referenced_docs:
            result += "\n\n---\n**Note**: This skill references these detailed documentation files:\n"
            for doc in referenced_docs[:5]:
                result += f"- {doc}\n"
            result += f"\nUse the `read_skill_file` tool to read them if needed."
        
        return result
    else:
        return f"Skill '{skill_name}' not found. Please check the skill name or try a different approach."


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
async def execute_code(ctx: RunContextWrapper[AgentContext], code: str = "") -> str:
    """
    Execute Python code and return the results.
    
    Use this tool when you need to:
    - Process files (Excel, PowerPoint, etc.)
    - Perform calculations or data transformations
    - Call MCP tools for external services
    - Generate output files
    
    The code runs in an isolated environment with these pre-injected helpers:
    - skill_path(skill_name, relative_path): Get path to skill resources
    - script_path(filename): Get path to user files in scripts/ directory
    - call_tool(tool_name, args): Call an MCP tool (async)
    - list_mcp_tools(): Discover available MCP tools (async)
    
    Important: Always end your code with a JSON status output using print(json.dumps({...}))
    
    Args:
        code: Python code to execute. Must be self-contained and executable. THIS PARAMETER IS REQUIRED.
    
    Returns:
        Execution results including stdout, stderr, and parsed JSON result.
    """
    context = ctx.context
    context.tool_call_count += 1
    
    # Validate code parameter - handle empty/missing code gracefully
    if not code or not code.strip():
        logger.warning(f"[Tool] execute_code called with empty code (call #{context.tool_call_count}), received: {repr(code)[:100]}")
        return """## Execution Error

**Status**: error

**Error**: The `code` parameter is empty or missing. This is a CRITICAL error.

**IMPORTANT**: The `execute_code` tool REQUIRES the `code` parameter to contain valid Python code.

**Correct usage example**:
```json
{
  "code": "import json\\nimport pandas as pd\\n\\n# Your code here\\nprint(json.dumps({'status': 'success', 'result': 'Done'}))"
}
```

**Common causes of this error**:
1. The code argument was not provided in the tool call
2. The code string was empty or contained only whitespace
3. The tool call JSON was malformed

**Action required**: Please retry by calling execute_code with the complete Python code in the `code` parameter. Make sure to:
1. Include ALL necessary imports at the top
2. Include the complete logic you want to execute
3. End with a print(json.dumps({...})) statement"""
    
    logger.info(f"[Tool] Executing code (call #{context.tool_call_count}), code length: {len(code)} chars")
    
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
    
    # Build result message
    exec_result = {
        "status": status,
        "stdout": "\n".join(output_lines),
        "stderr": "\n".join(error_lines),
        "result": result,
        "script_path": str(script_file),
        "output_files": output_files
    }
    
    # Format as readable string for the LLM
    result_str = f"## Execution Result\n\n**Status**: {status}\n\n"
    
    if output_lines:
        result_str += f"**Output**:\n```\n{exec_result['stdout']}\n```\n\n"
    
    if error_lines:
        result_str += f"**Errors**:\n```\n{exec_result['stderr']}\n```\n\n"
    
    if output_files:
        result_str += "**Generated Files**:\n"
        for f in output_files:
            result_str += f"- [{f['file_name']}]({f['file_url']}) ({f['file_size']} bytes)\n"
    
    if result:
        result_str += f"\n**Parsed Result**:\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
    
    return result_str


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
    - skill_path() and script_path() for file paths
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

def script_path(*parts) -> str:
    """Get relative path: scripts/<user_id>/[parts...]"""
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
