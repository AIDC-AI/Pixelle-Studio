"""
MCP Client - Tool routing and execution module.

Architecture:
- LLM loads Skills → Skills describe call_tool() usage patterns
- call_tool() routes to the correct MCP Server transparently
- LLM NEVER directly perceives MCP Servers or their tools

Key features:
- DEFAULT_MCP_SERVERS: Built-in servers, always available
- Lazy discovery: On first call to unknown tool, discovers all tools from all servers
- Fallback: If discovery fails, tries each server directly
- User-specific servers: Can be registered via register_tool_server()
"""
import asyncio
import os
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ============================================================================
# Default MCP Servers (built-in, always available)
# These are NOT visible to the LLM. Skills describe call_tool() usage.
# All use streamable-http protocol.
# ============================================================================

DEFAULT_MCP_SERVERS: List[Dict[str, str]] = [
    {
        "name": "gaode",
        "url": "https://mcp.api-inference.modelscope.net/41ac38014b984f/mcp",
        "type": "http",
        "description": "高德地图 MCP Server - 地图/地理/路线/POI相关工具",
    },
    {
        "name": "bing",
        "url": "https://mcp.api-inference.modelscope.net/710be47785c445/mcp",
        "type": "http",
        "description": "Bing搜索 MCP Server - 网页搜索",
    },
    {
        "name": "fetch",
        "url": "https://mcp.api-inference.modelscope.net/41c24891e80741/mcp",
        "type": "http",
        "description": "Fetch MCP Server - 网页抓取和内容提取",
    },
]

# ============================================================================
# Registry: tool_name → server_config
# ============================================================================

# Format: { "tool_name": { "url": "...", "type": "sse"|"http", "headers": ... } }
_TOOL_SERVER_MAP: Dict[str, Dict[str, Any]] = {}

# Track whether lazy discovery has been done
_discovery_done = False

# Track NO_PROXY to prevent infinite growth
_NO_PROXY_INITIALIZED = False


# ============================================================================
# Public API
# ============================================================================

def register_tool_server(tool_name: str, url: str, server_type: str = "sse", headers: dict = None):
    """
    Register a server configuration for a specific tool.
    Used for user-specific MCP servers (loaded from DB) or manual registration.
    """
    _TOOL_SERVER_MAP[tool_name] = {
        "url": url,
        "type": server_type,
        "headers": headers
    }


def get_registered_servers() -> Dict[str, Dict[str, str]]:
    """Get a copy of the current tool-to-server mapping."""
    return dict(_TOOL_SERVER_MAP)


def get_default_servers() -> List[Dict[str, str]]:
    """Get the list of default MCP servers (for inspection/debugging)."""
    return list(DEFAULT_MCP_SERVERS)


async def call_tool(tool_name: str, args: dict = None) -> Any:
    """
    Call an MCP tool. Routes to the correct server transparently.
    
    Routing priority:
    1. Explicitly registered tools (via register_tool_server)
    2. Lazy-discovered tools from DEFAULT_MCP_SERVERS
    3. Direct fallback: try each default server
    4. Mock fallback (for testing)
    
    Usage in Skills:
        result = call_tool('bing_search', {'query': '搜索词'})
        result = call_tool('fetch', {'url': 'https://example.com'})
    """
    args = args or {}
    
    # 1. Check explicitly registered tools
    server_config = _TOOL_SERVER_MAP.get(tool_name)
    if server_config:
        return await _call_real_tool(tool_name, args, server_config)
    
    # 2. Lazy discovery from default servers
    global _discovery_done
    if not _discovery_done:
        logger.info(f"[MCP Client] Tool '{tool_name}' not registered, starting lazy discovery...")
        await _discover_default_tools()
        
        server_config = _TOOL_SERVER_MAP.get(tool_name)
        if server_config:
            return await _call_real_tool(tool_name, args, server_config)
    
    # 3. Direct fallback: try each default server
    logger.info(f"[MCP Client] Tool '{tool_name}' not found after discovery, trying each default server...")
    for server in DEFAULT_MCP_SERVERS:
        try:
            config = {"url": server["url"], "type": server["type"]}
            result = await _call_real_tool(tool_name, args, config)
            # Success! Register for future use
            register_tool_server(tool_name, server["url"], server["type"])
            logger.info(f"[MCP Client] Found tool '{tool_name}' on {server['name']} server, registered for future use")
            return result
        except Exception as e:
            logger.debug(f"[MCP Client] Tool '{tool_name}' not on {server['name']}: {e}")
            continue
    
    # 4. Mock fallback
    logger.warning(f"[MCP Client] Tool '{tool_name}' not found on any server, using mock")
    return _call_mock_tool(tool_name, args)


async def discover_all_tools() -> List[Dict[str, Any]]:
    """
    Discover all tools from all default MCP servers.
    Returns a list of tool info dicts.
    Can be called explicitly (e.g. at app startup) or lazily on first call_tool.
    """
    all_tools = []
    
    for server in DEFAULT_MCP_SERVERS:
        try:
            tools = await _list_server_tools(server["url"], server["type"])
            for tool in tools:
                tool["server_name"] = server["name"]
                all_tools.append(tool)
        except Exception as e:
            logger.error(f"[MCP Client] Error discovering tools from {server['name']}: {e}")
    
    return all_tools


async def list_mcp_tools() -> list:
    """
    List all available MCP tools from registered servers + default servers.
    Returns a list of tool info dicts with name, description, and input schema.
    """
    _ensure_no_proxy()
    
    all_tools = []
    seen_servers = set()
    
    # 1. Collect unique servers from the registry
    servers_to_query = []
    for tool_name, config in _TOOL_SERVER_MAP.items():
        server_key = (config["url"], config.get("type", "sse"))
        if server_key not in seen_servers:
            seen_servers.add(server_key)
            servers_to_query.append(config)
    
    # 2. Add default servers (if not already queried)
    for server in DEFAULT_MCP_SERVERS:
        server_key = (server["url"], server["type"])
        if server_key not in seen_servers:
            seen_servers.add(server_key)
            servers_to_query.append({"url": server["url"], "type": server["type"]})
    
    if not servers_to_query:
        logger.info("[MCP Client] No MCP servers to query")
        return []
    
    # 3. Query each unique server
    for config in servers_to_query:
        try:
            tools = await _list_server_tools(config["url"], config.get("type", "sse"), config.get("headers"))
            all_tools.extend(tools)
        except Exception as e:
            logger.error(f"[MCP Client] Error querying tools from {config['url']}: {e}")
    
    return all_tools


# ============================================================================
# Internal: Discovery & Calling
# ============================================================================

async def _discover_default_tools():
    """
    Lazy discovery: query all default MCP servers and register their tools.
    Called once on first call_tool() to an unknown tool.
    """
    global _discovery_done
    if _discovery_done:
        return
    
    logger.info("[MCP Client] Starting lazy discovery of default MCP server tools...")
    
    for server in DEFAULT_MCP_SERVERS:
        try:
            tools = await _list_server_tools(server["url"], server["type"])
            registered_count = 0
            for tool in tools:
                tool_name = tool["name"]
                if tool_name not in _TOOL_SERVER_MAP:
                    register_tool_server(tool_name, server["url"], server["type"])
                    registered_count += 1
            logger.info(
                f"[MCP Client] Discovered {len(tools)} tools from {server['name']} "
                f"({server['url']}), registered {registered_count} new tools"
            )
        except Exception as e:
            logger.warning(f"[MCP Client] Failed to discover tools from {server['name']}: {e}")
    
    _discovery_done = True
    logger.info(f"[MCP Client] Discovery complete. Total registered tools: {len(_TOOL_SERVER_MAP)}")


async def _list_server_tools(
    url: str, 
    server_type: str = "sse", 
    headers: dict = None
) -> List[Dict[str, Any]]:
    """
    List tools from a single MCP server.
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client
    
    _ensure_no_proxy()
    
    tools = []
    
    try:
        async with asyncio.timeout(30):  # 30s timeout for discovery
            if server_type == "http":
                client_context = streamablehttp_client(url, headers=headers)
            else:
                client_context = sse_client(url, headers=headers)
            
            async with client_context as client_tuple:
                read, write = client_tuple[0], client_tuple[1]
                
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    for tool in tools_result.tools:
                        tools.append({
                            "name": tool.name,
                            "description": tool.description or "",
                            "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                            "server_url": url,
                        })
    except asyncio.TimeoutError:
        logger.warning(f"[MCP Client] Timeout listing tools from {url}")
    except Exception as e:
        logger.error(f"[MCP Client] Error listing tools from {url}: {e}")
        raise
    
    return tools


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
    
    _ensure_no_proxy()
    
    logger.info(f"[MCP Client] Calling tool '{tool_name}' on {url} (type: {server_type})...")
    
    MCP_CALL_TIMEOUT = 120  # 2 minutes max per tool call
    
    try:
        async with asyncio.timeout(MCP_CALL_TIMEOUT):
            if server_type == "http":
                client_context = streamablehttp_client(url, headers=headers)
            else:
                client_context = sse_client(url, headers=headers)
            
            async with client_context as client_tuple:
                read, write = client_tuple[0], client_tuple[1]
                
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=args)
                    
                    output = []
                    for content in result.content:
                        if content.type == 'text':
                            output.append(content.text)
                        elif content.type == 'image':
                            output.append(f"[Image: {content.mimeType}]")
                        elif content.type == 'resource':
                            output.append(f"[Resource: {content.uri}]")
                    
                    # Single text output → try JSON parse
                    if len(output) == 1 and isinstance(output[0], str):
                        try:
                            return json.loads(output[0])
                        except (json.JSONDecodeError, ValueError):
                            return output[0]
                    
                    # Multiple outputs → try JSON parse first
                    if output and isinstance(output[0], str):
                        try:
                            return json.loads(output[0])
                        except (json.JSONDecodeError, ValueError):
                            pass
                    
                    return output
    
    except asyncio.TimeoutError:
        logger.error(f"[MCP Client] TIMEOUT calling tool '{tool_name}' after {MCP_CALL_TIMEOUT}s")
        return {"error": f"Tool call timed out after {MCP_CALL_TIMEOUT} seconds"}
    
    except Exception as e:
        logger.error(f"[MCP Client] Error calling tool '{tool_name}': {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Internal: Helpers
# ============================================================================

def _ensure_no_proxy():
    """Ensure NO_PROXY is set correctly (only once per process)."""
    global _NO_PROXY_INITIALIZED
    if not _NO_PROXY_INITIALIZED:
        existing = os.environ.get("NO_PROXY", "")
        if "127.0.0.1" not in existing:
            os.environ["NO_PROXY"] = f"{existing},127.0.0.1,localhost" if existing else "127.0.0.1,localhost"
        _NO_PROXY_INITIALIZED = True


def _auto_register_from_env():
    """
    Auto-register MCP server from environment variables.
    Used by exec-spawned scripts to pick up user-specific server config.
    """
    mcp_url = os.environ.get("_MCP_SERVER_URL")
    mcp_type = os.environ.get("_MCP_SERVER_TYPE", "sse")
    
    if mcp_url and "__user_env__" not in _TOOL_SERVER_MAP:
        register_tool_server("__user_env__", mcp_url, mcp_type)
        logger.info(f"[MCP Client] Auto-registered user server from env: {mcp_url} ({mcp_type})")


def _call_mock_tool(tool_name: str, args: dict) -> Any:
    """Mock implementation for testing."""
    import time
    
    logger.warning(f"[MCP Client] Using MOCK for tool '{tool_name}' with args: {args}")
    time.sleep(0.5)
    
    if tool_name == 'google_drive':
        return {"files": ["mock_file_1.txt", "mock_file_2.pdf"]}
    elif tool_name == 'slack':
        return {"status": "sent", "timestamp": time.time()}
    
    return {"status": "ok", "data": f"Mock result from {tool_name}"}


async def upload_result(data):
    """Mock upload result to storage."""
    import hashlib
    
    data_str = json.dumps(data, sort_keys=True, default=str)
    ref_id = hashlib.md5(data_str.encode()).hexdigest()[:12]
    
    logger.info(f"[MCP Client] Uploading result (size: {len(data_str)} bytes)")
    return f"storage://results/{ref_id}"


# ============================================================================
# Auto-register on import (for exec-spawned subprocess environment)
# ============================================================================
_auto_register_from_env()
