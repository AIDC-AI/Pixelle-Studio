import asyncio
import os
import json
from typing import Dict, Any, Optional

# Registry of configured servers
# Format: { "tool_name": { "url": "...", "type": "sse" } }
_TOOL_SERVER_MAP: Dict[str, Dict[str, str]] = {}

def register_tool_server(tool_name: str, url: str, server_type: str = "sse"):
    """
    Register a server configuration for a specific tool.
    """
    _TOOL_SERVER_MAP[tool_name] = {
        "url": url,
        "type": server_type
    }
    # print(f"[MCP Client] Registered tool '{tool_name}' to {server_type} server: {url}")

async def call_tool(tool_name: str, args: dict = None) -> Any:
    """
    Call an MCP tool.
    If the tool is registered with a server, it makes a real MCP call.
    Otherwise, it falls back to mock implementation (for testing/default tools).
    """
    args = args or {}
    
    # Check if we have a real server for this tool
    server_config = _TOOL_SERVER_MAP.get(tool_name)
    
    if server_config:
        return await _call_real_tool(tool_name, args, server_config)
    
    # Fallback to mock implementation
    return _call_mock_tool(tool_name, args)

async def _call_real_tool(tool_name: str, args: dict, config: dict) -> Any:
    """
    Make a real MCP call via SSE.
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    
    url = config["url"]
    # Ensure NO_PROXY for localhost
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"
    
    print(f"[MCP Client] Calling real tool '{tool_name}' on {url}...")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Call the tool
                result = await session.call_tool(tool_name, arguments=args)
                
                # Result is a CallToolResult object
                # It has a 'content' attribute which is a list of Content objects (TextContent, ImageContent, etc.)
                # We need to parse this back to a simple structure for the script
                
                output = []
                for content in result.content:
                    if content.type == 'text':
                        output.append(content.text)
                    elif content.type == 'image':
                        output.append(f"[Image: {content.mimeType}]")
                    elif content.type == 'resource':
                        output.append(f"[Resource: {content.uri}]")
                        
                # If single text output, return it directly (common case)
                if len(output) == 1 and isinstance(output[0], str):
                    # Try to parse JSON if it looks like JSON
                    try:
                        return json.loads(output[0])
                    except:
                        return output[0]
                
                # If the tool returns a list (like user_topic_prompts_tool), we might need to handle it.
                # fastmcp tools usually return the direct value, which fastmcp wraps in TextContent.
                # If the return value was a list, fastmcp json-encodes it into the text.
                
                # Let's try to parse the first text content as JSON
                if output and isinstance(output[0], str):
                    try:
                        return json.loads(output[0])
                    except:
                        pass
                
                return output
                
    except Exception as e:
        print(f"[MCP Client] Error calling tool '{tool_name}': {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def _call_mock_tool(tool_name: str, args: dict) -> Any:
    """
    Mock implementation for default tools or testing.
    """
    import time
    import random
    
    print(f"[MCP Client] Calling MOCK tool '{tool_name}' with args: {args}")
    time.sleep(0.5)
    
    if tool_name == 'google_drive':
        return {"files": ["mock_file_1.txt", "mock_file_2.pdf"]}
    elif tool_name == 'slack':
        return {"status": "sent", "timestamp": time.time()}
        
    return {"status": "ok", "data": f"Mock result from {tool_name}"}

async def upload_result(data):
    """
    Mock upload result to storage.
    """
    import hashlib
    
    data_str = json.dumps(data, sort_keys=True, default=str)
    ref_id = hashlib.md5(data_str.encode()).hexdigest()[:12]
    
    print(f"[MCP Client] Uploading result (size: {len(data_str)} bytes)")
    return f"storage://results/{ref_id}"
