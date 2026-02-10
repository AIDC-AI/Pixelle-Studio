"""
Auto-generated MCP bootstrap for exec environment.
Provides call_tool() function transparently.

Default MCP servers (高德/Bing/Fetch) are built into app.mcp_client.
call_tool() auto-discovers and routes to the correct server.
"""
import os
import sys

def _setup_call_tool():
    """Setup call_tool in the exec environment."""
    # Ensure backend root is in sys.path
    backend_root = os.environ.get("PYTHONPATH", "").split(":")[0]
    if backend_root and backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    
    try:
        from app.mcp_client import call_tool as _async_call_tool
        
        # Optionally register user-specific MCP server from env vars
        mcp_url = os.environ.get("_MCP_SERVER_URL")
        mcp_type = os.environ.get("_MCP_SERVER_TYPE", "sse")
        if mcp_url:
            from app.mcp_client import register_tool_server
            register_tool_server("__user_env__", mcp_url, mcp_type)
        
        import asyncio
        
        def call_tool(tool_name, args=None):
            """
            Call an MCP tool synchronously.
            
            Built-in servers: 高德地图, Bing搜索, Fetch网页抓取
            Usage: result = call_tool('bing_search', {'query': 'search term'})
            """
            import asyncio
            from app.mcp_client import call_tool as _act
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        return pool.submit(asyncio.run, _act(tool_name, args or {})).result()
                else:
                    return loop.run_until_complete(_act(tool_name, args or {}))
            except RuntimeError:
                return asyncio.run(_act(tool_name, args or {}))
        
        return call_tool
    except ImportError as e:
        print(f"[MCP Bootstrap] Warning: Cannot import mcp_client: {e}")
        return None

# Auto-setup on import
_call_tool_func = _setup_call_tool()
if _call_tool_func:
    # Make call_tool available as a module-level function
    call_tool = _call_tool_func
