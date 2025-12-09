import os
import json
from openai import AsyncOpenAI

# LLM Configuration
LLM_BASE_URL = "https://REDACTED_BASE_URL_HOST/v1"
LLM_API_KEY = "REDACTED_API_KEY"
LLM_MODEL = "gemini-3-pro-preview"

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
