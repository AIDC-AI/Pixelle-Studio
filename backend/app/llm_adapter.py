import os
import json
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

# LLM Configuration
LLM_BASE_URL = "https://REDACTED_BASE_URL_HOST/v1"
LLM_API_KEY = "REDACTED_API_KEY"
LLM_MODEL = "gemini-3-pro-preview"


async def check_if_workflow_needed(user_prompt: str, tools: list, file_urls: list = None) -> Dict[str, Any]:
    """
    Check if the user's request requires a complex workflow or can be answered directly.
    Returns: {
        "needs_workflow": bool,
        "reasoning": str,
        "direct_answer": str (if needs_workflow is False)
    }
    """
    client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    
    # Prepare file context
    file_context = ""
    if file_urls:
        file_context = f"\n\nUser has uploaded the following files:\n" + "\n".join([f"- {url}" for url in file_urls])
    
    # Prepare tool summary
    tool_summary = ""
    if tools:
        tool_names = [t.get('name', 'unknown') for t in tools[:10]]  # Limit to first 10 for brevity
        tool_summary = f"\n\nAvailable tools: {', '.join(tool_names)}"
        if len(tools) > 10:
            tool_summary += f" (and {len(tools) - 10} more)"
    
    system_prompt = """
You are an intelligent task analyzer. Your job is to determine if a user's request requires:
1. A COMPLEX WORKFLOW: Multiple sequential tool calls, data transformations, or multi-step operations
2. A DIRECT ANSWER: Simple questions, information requests, or single-step operations

Return a JSON response with:
- "needs_workflow": true/false
- "reasoning": brief explanation
- "direct_answer": your answer (ONLY if needs_workflow is false)

Examples of requests that DON'T need workflow:
- "What is the URL of the file I just uploaded?"
- "Tell me about X"
- "Explain how Y works"
- "What tools are available?"
- Simple information queries

Examples of requests that NEED workflow:
- "Generate a video with X and then add music Y"
- "Process this image, enhance it, and create variations"
- "Search for X, summarize results, and create a report"
- Multi-step operations requiring tool orchestration
"""

    user_message = f"""
User request: {user_prompt}{file_context}{tool_summary}

Does this require a complex workflow with multiple tool calls, or can you answer directly?
"""

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )
    
    result = json.loads(response.choices[0].message.content)
    return result

async def generate_workflow_script(user_prompt: str, tools: list) -> str:
    """
    Generates a Python script based on the user prompt and available tools.
    """
    client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    
    from app.tool_search.selector import format_tools_for_llm
    
    # Format tools for OpenAI function calling
    formatted_tools = format_tools_for_llm(tools) if tools else []
    
    # Extract server configuration for injection into script
    tool_server_map = {}
    for t in tools:
        if 'server_url' in t:
            tool_server_map[t['name']] = {
                "url": t['server_url'],
                "type": t.get('server_type', 'sse'),
                "headers": t.get('server_headers', None)
            }
    
    system_prompt = """
You are an expert Python developer who generates workflow scripts.
Your goal is to write a Python script that orchestrates a workflow based on the user's request.

You have access to tools that will be provided separately. Use them as needed.

RULES:
1. The script MUST define an `async def main():` function.
2. The script MUST use `from app.mcp_client import call_tool, upload_result`.
3. The script MUST use `await call_tool('tool_name', {'arg': 'value'})` for all tool calls.
4. The script MUST return a dictionary with "status" and "summary" keys at the end of `main()`.
5. Do NOT import `mcp` or `fastmcp` directly. Use the provided `call_tool` wrapper.
6. Handle data dependencies between tools (output of one tool as input to next).
7. Use `print()` to log progress steps.
8. Return JSON-serializable result.
"""

    user_message = f"""
Generate a complete Python script to fulfill the following request:

"{user_prompt}"

Only return the Python code block. Do not include markdown formatting like ```python.
"""

    try:
        # Call LLM with tools parameter (MCP-compliant)
        llm_kwargs = {
            "model": LLM_MODEL,
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
        print(f"LLM generation failed: {e}")
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


async def generate_or_revise_script(
    user_message: str,
    tools: list,
    context_summary: str,
    previous_iteration: Optional[any] = None,
    file_urls: list = None
) -> str:
    """
    Generate or revise a workflow script based on context.
    
    Args:
        user_message: User's original request
        tools: Available tools
        context_summary: Context summary from ContextManager
        previous_iteration: Previous IterationRecord (if revising)
        file_urls: File URLs uploaded by user
        
    Returns:
        Generated/revised Python script
    """
    # Import here to avoid circular dependency
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from app.context.models import IterationRecord
    
    client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    
    from app.tool_search.selector import format_tools_for_llm
    
    # Format tools
    formatted_tools = format_tools_for_llm(tools) if tools else []
    
    # Extract server configuration
    tool_server_map = {}
    for t in tools:
        if 'server_url' in t:
            tool_server_map[t['name']] = {
                "url": t['server_url'],
                "type": t.get('server_type', 'sse')
            }
    
    system_prompt = """
You are an expert Python developer who generates workflow scripts.
Your goal is to write a Python script that orchestrates a workflow based on the user's request.

You have access to tools that will be provided separately. Use them as needed.

RULES:
1. The script MUST define an `async def main():` function.
2. The script MUST use `from app.mcp_client import call_tool, upload_result`.
3. The script MUST use `await call_tool('tool_name', {'arg': 'value'})` for all tool calls.
4. The script MUST return a dictionary with "status" and "summary" keys at the end of `main()`.
5. Do NOT import `mcp` or `fastmcp` directly. Use the provided `call_tool` wrapper.
6. Handle data dependencies between tools (output of one tool as input to next).
7. Use `print()` to log progress steps.
8. Return JSON-serializable result.
9. If this is a revision, carefully review the previous errors and fix them.
10. You should directly return the last tool's output as the final result when the output is not too large.

⚠️  CRITICAL - Tool Output Handling:
- Each tool returns data in a SPECIFIC format documented in its description's "Output Format" section.
- You MUST follow the exact output schema - do NOT write defensive code to handle multiple possible formats.
- Access returned fields directly as documented (e.g., if schema says 'rows', use result['rows']).
- Do NOT guess or add fallback logic for different return types - trust the schema.
- Example: If tool returns {"rows": [...], "count": 10}, directly use result['rows'] and result['count'].
"""
    
    # Prepare file URLs context
    file_context = ""
    if file_urls:
        file_context = "\n\nUser-uploaded files:\n" + "\n".join([f"- {url}" for url in file_urls])
        file_context += "\n(You can use these URLs as arguments when calling tools that accept file/image inputs)"
    
    # Build user message based on whether this is first generation or revision
    if previous_iteration is None:
        # First generation
        user_prompt = f"""
Generate a complete Python script to fulfill the following request:

"{user_message}"
{file_context}

Context:
{context_summary}

Only return the Python code block. Do not include markdown formatting like ```python.
"""
    else:
        # Revision mode - use the advice prompt
        if previous_iteration.revision_advice:
            user_prompt = previous_iteration.revision_advice.llm_prompt
            # Add file context if not already included
            if file_urls and "User-uploaded files" not in user_prompt:
                user_prompt = user_prompt + file_context
        else:
            # Fallback if no advice available
            user_prompt = f"""
The previous script failed. Please revise it.
{file_context}

Context:
{context_summary}

Generate a REVISED Python script that fixes the issues.
Only return the Python code block.
"""
    
    try:
        # Call LLM
        llm_kwargs = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
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
        # Fallback error script
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
            server_config_code += f"register_tool_server('{tool_name}', '{config['url']}', '{config['type']}')\n"
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
