export interface MCPTool {
    name: string;
    description: string;
}

export interface MCPServer {
  id: string
  name: string
  transport: 'streamable-http' | 'sse' | 'stdio'
  url?: string  // for streamable-http/SSE
  command?: string  // for stdio
  args?: string[]  // for stdio
  status: 'connected' | 'disconnected' | 'error'
  tools?: MCPTool[]
  error?: string
}