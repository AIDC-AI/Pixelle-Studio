# Copyright (C) 2026 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import os
import json
from typing import Dict, Any, Optional

# Registry of configured servers
# Format: { "tool_name": { "url": "...", "type": "sse" } }
_TOOL_SERVER_MAP: Dict[str, Dict[str, str]] = {}

def register_tool_server(tool_name: str, url: str, server_type: str = "sse", headers: dict = None):
    """
    Register a server configuration for a specific tool.
    """
    _TOOL_SERVER_MAP[tool_name] = {
        "url": url,
        "type": server_type,
        "headers": headers
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
    Make a real MCP call via SSE or HTTP Streamable.
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client
    
    url = config["url"]
    server_type = config.get("type", "sse")
    headers = config.get("headers", None)
    
    # Ensure NO_PROXY for localhost
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"
    
    print(f"[MCP Client] Calling real tool '{tool_name}' on {url} (type: {server_type})...")
    
    try:
        # Choose the appropriate client based on server type
        if server_type == "http":
            client_context = streamablehttp_client(url, headers=headers)
        else:  # Default to SSE
            client_context = sse_client(url, headers=headers)
        
        async with client_context as client_tuple:
            # For streamablehttp_client, we get (read, write, get_auth_header)
            # For sse_client, we get (read, write)
            read, write = client_tuple[0], client_tuple[1]
            
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

async def list_mcp_tools() -> list:
    """
    List all available MCP tools from registered servers.
    Returns a list of tool info dicts with name, description, and input schema.
    
    This is a fallback mechanism for when no skill matches - allows LLM to 
    discover available tools dynamically.
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client
    
    # Ensure NO_PROXY for localhost
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"
    
    all_tools = []
    seen_servers = set()  # Avoid duplicate server connections
    
    # Collect unique servers from the registry
    servers_to_query = []
    for tool_name, config in _TOOL_SERVER_MAP.items():
        server_key = (config["url"], config.get("type", "sse"))
        if server_key not in seen_servers:
            seen_servers.add(server_key)
            servers_to_query.append(config)
    
    # If no tools registered, return empty list
    if not servers_to_query:
        print("[MCP Client] No MCP servers registered, returning empty tool list")
        return []
    
    # Query each unique server for its tools
    for config in servers_to_query:
        url = config["url"]
        server_type = config.get("type", "sse")
        headers = config.get("headers", None)
        
        print(f"[MCP Client] Querying tools from {url} (type: {server_type})...")
        
        try:
            if server_type == "http":
                client_context = streamablehttp_client(url, headers=headers)
            else:
                client_context = sse_client(url, headers=headers)
            
            async with client_context as client_tuple:
                read, write = client_tuple[0], client_tuple[1]
                
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # List tools from this server
                    tools_result = await session.list_tools()
                    
                    for tool in tools_result.tools:
                        tool_info = {
                            "name": tool.name,
                            "description": tool.description or "",
                            "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                            "server_url": url,
                        }
                        all_tools.append(tool_info)
                        
            print(f"[MCP Client] Found {len(tools_result.tools)} tools from {url}")
            
        except Exception as e:
            print(f"[MCP Client] Error querying tools from {url}: {e}")
            import traceback
            traceback.print_exc()
    
    return all_tools


def get_registered_servers() -> Dict[str, Dict[str, str]]:
    """
    Get a copy of the current tool-to-server mapping.
    Useful for debugging or inspection.
    """
    return dict(_TOOL_SERVER_MAP)


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
