import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

class MCPServer(BaseModel):
    id: str
    name: str
    type: str  # 'sse', 'stdio', 'http'
    config: Dict[str, Any]
    enabled: bool
    headers: dict | None = None

class MCPServerConfig(BaseModel):
    servers: List[MCPServer]

class MCPAggregator:
    def __init__(self):
        self.tools = []

    async def fetch_tools(self, config: MCPServerConfig) -> List[Dict[str, Any]]:
        """
        Connect to all enabled servers in the config and fetch their tools.
        """
        aggregated_tools = []

        for server in config.servers:
            if not server.enabled:
                continue
            
            try:
                if server.type == 'sse':
                    tools = await self._fetch_sse_tools(server)
                    aggregated_tools.extend(tools)
                elif server.type == 'stdio':
                    # TODO: Implement stdio support
                    # tools = await self._fetch_stdio_tools(server)
                    # aggregated_tools.extend(tools)
                    print(f"Stdio support not yet implemented for server: {server.name}")
                elif server.type == 'http':
                     # Treat 'http' as SSE for now based on current UI implementation
                     # or if it's a simple HTTP endpoint, we need a different client.
                     # Assuming SSE for 'http' type if it points to an SSE endpoint.
                     # But let's stick to 'sse' type for SSE.
                     if server.config.get('endpoint'):
                         # If it's just a raw HTTP endpoint, we might need a different logic
                         # For now, let's assume the user selects 'sse' for SSE servers.
                         pass
            except Exception as e:
                print(f"Error fetching tools from server {server.name}: {e}")
        
        # Only add default mock tools if no servers are configured or no tools were fetched
        if not aggregated_tools:
            aggregated_tools.extend(self._get_default_tools())
        
        self.tools = aggregated_tools
        return aggregated_tools

    async def _fetch_sse_tools(self, server: MCPServer) -> List[Dict[str, Any]]:
        url = server.config.get('url')
        if not url:
            return []

        print(f"[MCPAggregator] Connecting to SSE server: {url}")
        
        # Ensure we don't use proxy for localhost
        import os
        os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"
        
        try:
            # Configure sse_client with timeout and no proxy if possible (though sse_client might not expose all httpx options directly)
            # We rely on environment variables for proxy settings if needed.
            print(f"[MCPAggregator] Headers: {server.headers}")
            async with sse_client(url, headers=server.headers) as (read, write):
                print(f"[MCPAggregator] SSE connection established to {url}")
                async with ClientSession(read, write) as session:
                    print(f"[MCPAggregator] Initializing session with {url}")
                    await session.initialize()
                    
                    print(f"[MCPAggregator] Listing tools from {url}")
                    result = await session.list_tools()
                    
                    tools = []
                    for tool in result.tools:
                        tools.append({
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema,
                            "server_id": server.id,
                            "server_url": url,
                            "server_type": "sse"
                        })
                    
                    print(f"[MCPAggregator] Fetched {len(tools)} tools from {server.name}")
                    return tools
        except Exception as e:
            print(f"[MCPAggregator] Failed to connect/fetch from SSE server {url}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Return empty list instead of raising to allow other servers to work
            return []

    def _get_default_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "google_drive",
                "description": "Access Google Drive files",
                "functions": ["list_files", "read_file"]
            },
            {
                "name": "slack",
                "description": "Send messages to Slack",
                "functions": ["send_message"]
            }
        ]
