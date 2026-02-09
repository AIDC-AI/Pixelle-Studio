"""
LLM Adapter - Manages LLM interactions with skills-based workflow.

This module provides:
1. Skills-aware system prompt with metadata injection
2. Script generation based on SKILL.md guidance
3. Support for both pure Python execution and MCP tool calls

LLM Configuration:
- OPENAI_API_KEY, OPENAI_BASE_URL: Automatically read from environment variables by OpenAI SDK
- OPENAI_MODEL: Model name, default gpt-4o
"""

import logging
import os
import json
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI

from app.skills.loader import get_skill_loader
from app.mcp_aggregator import MCPServerConfig

# LLM Configuration - read from environment variables, supports custom configuration
# LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://REDACTED_BASE_URL_HOST/v1")
# LLM_API_KEY = os.getenv("LLM_API_KEY", "REDACTED_API_KEY")
# LLM_MODEL = os.getenv("LLM_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

def build_skills_system_prompt(skills_meta: str, skill_content: Optional[str] = None) -> str:
    """
    Build system prompt with skills metadata and optional full skill content.
    
    Args:
        skills_meta: Skills metadata section (from SkillLoader.build_skills_meta_prompt())
        skill_content: Optional full SKILL.md content for the selected skill
        
    Returns:
        Complete system prompt string
    """
    base_prompt = """You are an intelligent workflow agent with access to specialized skills.

Your workflow:
1. Analyze the user's request
2. Determine if a skill is needed (check Available Skills below)
3. If a skill is relevant, use the read_skill tool to load its full documentation
4. Generate Python code following the skill's guidance and templates
5. Execute the code and return results

## Code Generation Rules

When generating Python code:
1. The script MUST define an `async def main():` function
2. The script MUST return a dictionary with "status" and "summary" keys
3. Use `print()` to log progress steps
4. Return JSON-serializable result
5. Follow the patterns and templates from the loaded skill

### For Pure Python Tasks (like Excel processing):
- Use standard libraries like pandas, openpyxl directly
- Can call helper scripts from the skill directory
- Example: `subprocess.run(['python', 'skills/xlsx/recalc.py', 'output.xlsx'])`

### For MCP Tool Tasks (like video generation):
- Use `from app.mcp_client import call_tool`
- Call tools with `await call_tool('tool_name', {'arg': 'value'})`

"""
    
    # Add skills metadata
    prompt_parts = [base_prompt, skills_meta]
    
    # Add full skill content if provided
    if skill_content:
        prompt_parts.append("\n## Loaded Skill Documentation\n")
        prompt_parts.append(skill_content)
    
    return "\n".join(prompt_parts)



async def generate_workflow_script(user_prompt: str, tools: list, config_to_use: MCPServerConfig = None) -> str:
    """
    Generates a Python script based on the user prompt and available tools.
    """
    client = AsyncOpenAI()

    from app.tool_search.selector import format_tools_for_llm

    # Format tools for OpenAI function calling
    formatted_tools = format_tools_for_llm(tools) if tools else []
    headers = config_to_use.servers[0].headers if config_to_use else None
    # Extract server configuration for injection into script
    tool_server_map = {}
    for t in tools:
        if 'server_url' in t:
            tool_server_map[t['name']] = {"url": t['server_url'], "type": t.get('server_type', 'sse'), "headers": headers}

    system_prompt = """
You are an expert Python developer who generates workflow scripts.
Your goal is to write a Python script that orchestrates a workflow based on the user's request.

You have access to tools that will be provided separately. Use them as needed.

RULES:
1. The script MUST define an `async def main():` function.
2. The script MUST use `from app.mcp_client import call_tool, upload_result`.
3. The script MUST use `await call_tool('tool_name', {'arg': 'value'})` for all tool calls.
4. The script MUST use `await upload_result(result)` to upload the result of the tool call.
5. The script MUST return a dictionary with "status" and "summary" keys at the end of `main()`.
6. Do NOT import `mcp` or `fastmcp` directly. Use the provided `call_tool` wrapper.
7. Handle data dependencies between tools (output of one tool as input to next).
8. Use `print()` to log progress steps.
9. Return JSON-serializable result.
"""

    user_message = f"""
Generate a complete Python script to fulfill the following request:

"{user_prompt}"

Only return the Python code block. Do not include markdown formatting like ```python.
"""

    try:
        # Call LLM with tools parameter (MCP-compliant)
        llm_kwargs = {
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        }
        
        # Only add tools if we have them
        if formatted_tools:
            llm_kwargs["tools"] = formatted_tools
        
        response = await client.chat.completions.create(**llm_kwargs)
        
        generated_code = response.choices[0].message.content
        
        # Clean up markdown code blocks if present
        if generated_code.startswith("```python"):
            generated_code = generated_code[9:]
        if generated_code.startswith("```"):
            generated_code = generated_code[3:]
        if generated_code.endswith("```"):
            generated_code = generated_code[:-3]
            
        generated_code = generated_code.strip()
        
    except Exception as e:        
        print(f"LLM generation failed,request message: {llm_kwargs}, error: {e}")
        # Fallback to a simple error script
        return f"""
import asyncio
import json

async def main():
    print("Error generating script: {str(e)}")
    return {{"status": "error", "message": "{str(e)}"}}

if __name__ == "__main__":
    print(json.dumps(asyncio.run(main())))
"""

    # Inject server configuration
    server_config_code = ""
    if tool_server_map:
        server_config_code = "from app.mcp_client import register_tool_server\n\n"
        for tool_name, config in tool_server_map.items():
            server_config_code += f"register_tool_server('{tool_name}', '{config['url']}', '{config['type']}', {config['headers']})\n"
        server_config_code += "\n"

    # Assemble final script
    final_script = f"""
import sys
import asyncio
import json
import os
from app.mcp_client import call_tool, upload_result

# Server Configuration
{server_config_code}

{generated_code}

if __name__ == "__main__":
    try:
        # Run the async main function
        result = asyncio.run(main())
        # Print the result as the last line of stdout
        print(json.dumps(result))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({{"status": "error", "error": str(e)}}))
"""
    return final_script


async def generate_script_with_skill(
    user_message: str,
    skill_name: Optional[str] = None,
    file_urls: List[str] = None,
    context_summary: str = "",
    previous_iteration: Optional[Any] = None,
    mcp_tools: List[Dict] = None
) -> str:
    """
    Generate a Python script using skill guidance.
    
    Args:
        user_message: User's original request
        skill_name: Name of the skill to use (optional)
        file_urls: File URLs uploaded by user
        context_summary: Context summary from previous iterations
        previous_iteration: Previous IterationRecord (if revising)
        mcp_tools: MCP tools if needed (optional)
        
    Returns:
        Generated Python script
    """
    client = AsyncOpenAI()
    skill_loader = get_skill_loader()
    
    # Get skills metadata
    skills_meta = skill_loader.build_skills_meta_prompt()
    
    # Load full skill content if skill_name provided
    skill_content = None
    skill_directory = None
    if skill_name:
        skill_content = skill_loader.read_skill(skill_name)
        skill_directory = skill_loader.get_skill_directory(skill_name)
    
    # Build system prompt
    system_prompt = build_skills_system_prompt(skills_meta, skill_content)
    
    # Add skill directory info if available
    if skill_directory:
        system_prompt += f"\n\n## Skill Directory\nThe skill's helper scripts are located at: {skill_directory}\n"
        system_prompt += f"You can call them using subprocess, e.g.: subprocess.run(['python', '{skill_directory}/recalc.py', 'file.xlsx'])\n"
    
    # Prepare file URLs context
    file_context = ""
    if file_urls:
        file_context = "\n\nUser-uploaded files:\n" + "\n".join([f"- {url}" for url in file_urls])
        file_context += "\n(You can use these file paths/URLs directly in your code)"
    
    # Build user prompt based on whether this is first generation or revision
    if previous_iteration is None:
        # First generation
        user_prompt = f"""Generate a complete Python script to fulfill the following request:

"{user_message}"
{file_context}

{context_summary if context_summary else ""}

IMPORTANT:
1. Follow the patterns and templates from the skill documentation above
2. Return ONLY the Python code, no markdown formatting
3. The script must have an async def main() function that returns a dict with "status" and "summary"
"""
    else:
        # Revision mode
        if previous_iteration.revision_advice:
            user_prompt = previous_iteration.revision_advice.llm_prompt
            if file_urls and "User-uploaded files" not in user_prompt:
                user_prompt = user_prompt + file_context
        else:
            user_prompt = f"""The previous script failed. Please revise it.
{file_context}

Context:
{context_summary}

Generate a REVISED Python script that fixes the issues.
Only return the Python code block.
"""
    
    try:
        # Call LLM
        llm_kwargs = {
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        # Add MCP tools if provided (for tool-based skills)
        if mcp_tools:
            from app.tool_search.selector import format_tools_for_llm
            formatted_tools = format_tools_for_llm(mcp_tools)
            if formatted_tools:
                llm_kwargs["tools"] = formatted_tools
        
        response = await client.chat.completions.create(**llm_kwargs)
        
        generated_code = response.choices[0].message.content
        
        # Clean up markdown code blocks
        if generated_code.startswith("```python"):
            generated_code = generated_code[9:]
        if generated_code.startswith("```"):
            generated_code = generated_code[3:]
        if generated_code.endswith("```"):
            generated_code = generated_code[:-3]
        
        generated_code = generated_code.strip()
        
    except Exception as e:
        print(f"LLM generation failed: {e}")
        return _create_error_script(str(e))
    
    # Build final script with proper wrapper
    return _wrap_script(generated_code, mcp_tools, skill_directory)


def _create_error_script(error_message: str) -> str:
    """Create an error script when generation fails."""
    return f'''import asyncio
import json

async def main():
    print("Error generating script: {error_message}")
    return {{"status": "error", "message": "{error_message}"}}

if __name__ == "__main__":
    print(json.dumps(asyncio.run(main())))
'''


def _wrap_script(generated_code: str, mcp_tools: List[Dict] = None, skill_directory: str = None) -> str:
    """
    Wrap generated code with necessary imports and execution framework.
    
    Args:
        generated_code: The LLM-generated code
        mcp_tools: MCP tools if any (for server configuration)
        skill_directory: Path to skill directory for helper scripts
        
    Returns:
        Complete executable script
    """
    # Build imports section
    imports = [
        "import sys",
        "import asyncio",
        "import json",
        "import os",
        "import subprocess",
        "from pathlib import Path"
    ]
    
    # Add MCP client import if tools are used
    mcp_config = ""
    if mcp_tools:
        imports.append("from app.mcp_client import call_tool, upload_result, register_tool_server")
        
        # Extract server configuration
        tool_server_map = {}
        for t in mcp_tools:
            if 'server_url' in t:
                tool_server_map[t['name']] = {
                    "url": t['server_url'],
                    "type": t.get('server_type', 'sse')
                }
        
        if tool_server_map:
            mcp_config = "\n# MCP Server Configuration\n"
            for tool_name, config in tool_server_map.items():
                mcp_config += f"register_tool_server('{tool_name}', '{config['url']}', '{config['type']}')\n"
    
    # Add skill directory as constant if provided
    skill_dir_config = ""
    if skill_directory:
        skill_dir_config = f"\n# Skill directory for helper scripts\nSKILL_DIR = '{skill_directory}'\n"
    
    # Assemble final script
    final_script = f'''{chr(10).join(imports)}
{mcp_config}
{skill_dir_config}

{generated_code}

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        print(json.dumps(result))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({{"status": "error", "error": str(e)}}))
'''
    
    return final_script


# ============================================================================
# Legacy functions for backward compatibility
# ============================================================================

async def generate_workflow_script(user_prompt: str, tools: list) -> str:
    """
    Legacy function - generates a Python script based on the user prompt and available tools.
    Kept for backward compatibility.
    """
    return await generate_script_with_skill(
        user_message=user_prompt,
        mcp_tools=tools
    )


async def generate_script_with_skill(
    user_message: str,
    tools: list,
    context_summary: str,
    previous_iteration: Optional[Any] = None,
    file_urls: list = None
) -> str:
    """
    Legacy function - generate or revise a workflow script based on context.
    Kept for backward compatibility.
    """
    # Try to detect skill from context or use no skill
    skill_loader = get_skill_loader()
    skills = skill_loader.scan_skills()
    
    # Simple skill detection based on file types
    suggested_skill = None
    if file_urls:
        for url in file_urls:
            if any(url.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.csv']):
                suggested_skill = 'xlsx'
                break
    
    return await generate_script_with_skill(
        user_message=user_message,
        skill_name=suggested_skill,
        file_urls=file_urls,
        context_summary=context_summary,
        previous_iteration=previous_iteration,
        mcp_tools=tools
    )
