"""
Tools for SkillAgent - Native OpenAI API implementation.

This module defines:

Exposed Tools (LLM can call directly via tool_calls):
1. load_skill - Load skill documentation (SKILL.md)
2. read_skill_file - Read a specific file from skill directory
3. list_skill_tree - List skill directory structure
4. list_mcp_tools - Discover available MCP tools

Internal Functions (auto-triggered by system):
- execute_code_internal - Execute Python code from <execute> blocks
  (Not exposed to LLM - triggered implicitly when detecting code blocks)

Key exports:
- TOOL_SCHEMAS: OpenAI API format tool definitions
- TOOL_HANDLERS: Tool name -> handler function mapping
- execute_code_internal: For implicit code execution
"""

import os
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

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
    last_response_text: str = ""  # Store last LLM response for synthetic tool call
    
    def __post_init__(self):
        """Ensure script_dir exists."""
        self.script_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Tool Implementations (Plain async functions, no decorators)
# =============================================================================

async def load_skill(context: AgentContext, skill_name: str) -> str:
    """
    Load skill documentation (SKILL.md) for domain-specific guidance.
    
    Args:
        context: AgentContext with user_id, skill_loader, etc.
        skill_name: Name of the skill to load (e.g., "xlsx", "pptx", "video")
    
    Returns:
        JSON string with skill content and metadata.
    """
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
        
        result = {
            "__tool__": "load_skill",
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


async def read_skill_file(context: AgentContext, skill_name: str, file_path: str) -> str:
    """
    Read a specific file from a skill's directory.
    
    Args:
        context: AgentContext
        skill_name: Name of the skill (e.g., "xlsx", "pptx")
        file_path: Relative path to the file within the skill directory
    
    Returns:
        The file content as a string, or an error message.
    """
    user_id = context.user_id
    skill_loader = context.skill_loader
    
    logger.info(f"[Tool] Reading skill file: {skill_name}/{file_path}")
    
    file_content = skill_loader.read_skill_file(skill_name, file_path, user_id)
    
    if file_content:
        return f"# Content of '{skill_name}/{file_path}'\n\n```\n{file_content}\n```"
    else:
        return f"File '{skill_name}/{file_path}' not found or not readable. Please check the path or use `list_skill_tree` to see available files."


async def list_skill_tree(context: AgentContext, skill_name: str) -> str:
    """
    List the directory structure of a skill.
    
    Args:
        context: AgentContext
        skill_name: Name of the skill (e.g., "xlsx", "pptx")
    
    Returns:
        A JSON representation of the directory tree.
    """
    user_id = context.user_id
    skill_loader = context.skill_loader
    
    logger.info(f"[Tool] Listing skill tree: {skill_name}")
    
    tree = skill_loader.list_skill_tree(skill_name, user_id)
    
    if tree:
        tree_json = json.dumps(tree, indent=2, ensure_ascii=False)
        return f"# Directory structure of skill '{skill_name}'\n\n```json\n{tree_json}\n```\n\nYou can use `read_skill_file` to read specific files."
    else:
        return f"Skill '{skill_name}' not found. Please check the skill name."


async def list_mcp_tools(context: AgentContext) -> str:
    """
    Discover all available MCP tools from registered servers.
    
    Args:
        context: AgentContext with mcp_server_url, mcp_server_type
    
    Returns:
        A formatted list of available MCP tools.
    """
    from app.mcp_client import list_mcp_tools as mcp_list_tools, register_tool_server, _TOOL_SERVER_MAP
    
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
        
        result += "\nUse `await call_tool('tool_name', {...})` in your <execute> block to call these tools."
        
        return result
        
    except Exception as e:
        logger.error(f"[Tool] Error listing MCP tools: {e}")
        return f"Error listing MCP tools: {str(e)}"


async def execute_code_internal(context: AgentContext, code: str) -> str:
    """
    Internal function to execute Python code. 
    
    This is NOT exposed to LLM - it's called internally by the agent's auto-loop mechanism
    when detecting <execute> blocks in LLM responses.
    
    Args:
        context: AgentContext with user_id, script_dir, etc.
        code: Python code to execute
    
    Returns:
        JSON string with execution results (stdout, stderr, output_files, etc.)
    """
    context.tool_call_count += 1
    logger.info(f"[Tool] execute_code_internal called (call #{context.tool_call_count}), code length: {len(code)} chars")
    
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
    
    # ========== FALLBACK STRATEGY: Record files before execution ==========
    # Get parent scripts/ directory (to detect files wrongly placed there)
    scripts_parent_dir = context.script_dir.parent  # This is scripts/
    files_before_exec = set()
    if scripts_parent_dir.exists():
        # Only track files directly in scripts/ (not in subdirectories)
        files_before_exec = {f.name for f in scripts_parent_dir.iterdir() if f.is_file()}
    
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
    
    # ========== FALLBACK STRATEGY: Detect and move misplaced files ==========
    misplaced_files_moved = []
    if scripts_parent_dir.exists():
        files_after_exec = {f.name for f in scripts_parent_dir.iterdir() if f.is_file()}
        new_files_in_parent = files_after_exec - files_before_exec
        
        # Move any new files from scripts/ to scripts/<user_id>/
        for filename in new_files_in_parent:
            # Skip Python script files (our own execution scripts)
            if filename.endswith('.py'):
                continue
            
            src_path = scripts_parent_dir / filename
            dst_path = context.script_dir / filename
            
            try:
                import shutil
                shutil.move(str(src_path), str(dst_path))
                misplaced_files_moved.append(filename)
                logger.warning(f"[Fallback] Moved misplaced file: scripts/{filename} -> scripts/{context.user_id or 'default'}/{filename}")
            except Exception as e:
                logger.error(f"[Fallback] Failed to move misplaced file {filename}: {e}")
    
    # Check for output files and generate URLs
    output_files = []
    output_files_set = set()  # Track which files we've already added
    
    if result and isinstance(result, dict):
        # Try output_files first (new format)
        raw_output_files = result.get("output_files", [])
        if raw_output_files:
            for item in raw_output_files:
                if isinstance(item, dict):
                    file_name = item.get("filename") or item.get("file_name")
                elif isinstance(item, str):
                    file_name = item
                else:
                    continue
                
                if file_name:
                    # Strip any path prefix (handle cases like "scripts/xxx" or full paths)
                    file_name = Path(file_name).name
                    file_path = context.script_dir / file_name
                    if file_path.exists() and file_name not in output_files_set:
                        path_prefix = f"{context.user_id}/" if context.user_id else "default/"
                        file_url = f"http://{LOCAL_IP}:{SERVER_PORT}/f/{path_prefix}{file_name}"
                        output_files.append({
                            "file_name": file_name,
                            "file_url": file_url,
                            "file_size": file_path.stat().st_size
                        })
                        output_files_set.add(file_name)
        
        # Fallback to output_file_names (legacy format)
        if not output_files:
            output_file_names = result.get("output_file_names", [])
            if output_file_names:
                for file_name in output_file_names:
                    # Strip any path prefix
                    file_name = Path(file_name).name
                    file_path = context.script_dir / file_name
                    if file_path.exists() and file_name not in output_files_set:
                        path_prefix = f"{context.user_id}/" if context.user_id else "default/"
                        file_url = f"http://{LOCAL_IP}:{SERVER_PORT}/f/{path_prefix}{file_name}"
                        output_files.append({
                            "file_name": file_name,
                            "file_url": file_url,
                            "file_size": file_path.stat().st_size
                        })
                        output_files_set.add(file_name)
    
    # ========== FALLBACK STRATEGY: Add misplaced files that were moved ==========
    # Even if LLM didn't report these files correctly, we moved them, so add them to output
    for file_name in misplaced_files_moved:
        if file_name not in output_files_set:
            file_path = context.script_dir / file_name
            if file_path.exists():
                path_prefix = f"{context.user_id}/" if context.user_id else "default/"
                file_url = f"http://{LOCAL_IP}:{SERVER_PORT}/f/{path_prefix}{file_name}"
                output_files.append({
                    "file_name": file_name,
                    "file_url": file_url,
                    "file_size": file_path.stat().st_size
                })
                output_files_set.add(file_name)
                logger.info(f"[Fallback] Added recovered file to output: {file_name}")
    
    # Build structured result
    exec_result = {
        "__tool__": "execute_code",
        "status": status,
        "stdout": "\n".join(output_lines),
        "stderr": "\n".join(error_lines),
        "result": result,
        "script_path": str(script_file),
        "output_files": output_files
    }
    
    return json.dumps(exec_result, ensure_ascii=False)


def _build_skill_helpers_code(context: AgentContext) -> str:
    """
    Build the skill_helpers module code to inject into execution environment.
    """
    # Build MCP server registration if configured
    mcp_setup = ""
    if context.mcp_server_url:
        mcp_setup = f'''
# Register default MCP server for all tools
_DEFAULT_MCP_SERVER = "{context.mcp_server_url}"
_DEFAULT_MCP_TYPE = "{context.mcp_server_type}"

from app.mcp_client import _TOOL_SERVER_MAP, register_tool_server
if not _TOOL_SERVER_MAP:
    register_tool_server("__default__", _DEFAULT_MCP_SERVER, _DEFAULT_MCP_TYPE)

_original_call_tool = call_tool
async def call_tool(tool_name: str, args: dict = None):
    if tool_name not in _TOOL_SERVER_MAP:
        register_tool_server(tool_name, _DEFAULT_MCP_SERVER, _DEFAULT_MCP_TYPE)
    return await _original_call_tool(tool_name, args)
'''
    
    # Get skill paths map for current user
    skills = context.skill_loader.scan_skills(context.user_id)
    skill_paths_map = {s.name: s.directory for s in skills}
    
    script_subdir = context.user_id if context.user_id else "default"
    
    return f'''
# === Skill Helpers (auto-injected) ===
import os
import json

_SKILL_PATHS = {json.dumps(skill_paths_map)}
SCRIPTS_ROOT = "scripts/{script_subdir}"

def skill_path(skill_name: str, *parts) -> str:
    """Get relative path: skills/<source>/<skill_name>/[parts...]"""
    base_path = _SKILL_PATHS.get(skill_name)
    if not base_path:
        return os.path.join("skills", "default", skill_name, *parts)
    return os.path.join(base_path, *parts)

def user_file(*parts) -> str:
    """Get path to user's working files: scripts/<user_id>/[parts...]"""
    return os.path.join(SCRIPTS_ROOT, *parts)

import sys
sys.path.insert(0, '.')
from app.mcp_client import call_tool, list_mcp_tools
{mcp_setup}
# === End Skill Helpers ===
'''


# =============================================================================
# Tool Schemas for OpenAI API (not including execute_code - it's implicit)
# =============================================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "Load detailed documentation for a specific skill domain (Excel, PowerPoint, video generation, etc.). Use this when you need guidance on how to accomplish a domain-specific task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill to load (e.g., 'xlsx', 'pptx', 'video', 'social-media-video')"
                    }
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_skill_file",
            "description": "Read a specific file from a skill's directory, such as detailed documentation, helper scripts, templates, or configuration files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill (e.g., 'xlsx', 'pptx')"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Relative path to the file within the skill directory (e.g., 'html2pptx.md', 'scripts/helper.py')"
                    }
                },
                "required": ["skill_name", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skill_tree",
            "description": "List the directory structure of a skill to discover available files like documentation, scripts, templates, or resources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill (e.g., 'xlsx', 'pptx')"
                    }
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_mcp_tools",
            "description": "Discover all available MCP tools from registered servers. Use this when you need external services like image generation, audio synthesis, etc.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# =============================================================================
# Tool Handlers Mapping
# =============================================================================

TOOL_HANDLERS: Dict[str, Any] = {
    "load_skill": load_skill,
    "read_skill_file": read_skill_file,
    "list_skill_tree": list_skill_tree,
    "list_mcp_tools": list_mcp_tools,
    # Note: execute_code is NOT here - it's handled separately via Synthetic Tool Call
}
