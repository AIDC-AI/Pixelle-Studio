export interface MCPToolInputSchema {
  type?: string
  properties?: Record<string, {
    type?: string
    description?: string
  }>
  required?: string[]
}

export interface MCPTool {
    name: string
    description?: string
    inputSchema?: MCPToolInputSchema
    outputSchema?: any
    server_id?: string
    server_name?: string
    server_url?: string
    server_type?: string
}

export type TransportType = 'streamable-http' | 'sse' | 'stdio'

export interface MCPServer {
  id: string
  name: string
  transport: TransportType
  url?: string | null
  headers?: string | null  // JSON string for custom headers (e.g. {"Authorization": "Bearer ..."})
  command?: string | null
  args?: string | null
  error?: string | null
  uid: number
  created_at: string
  updated_at: string
  
  // Status info (returned from backend)
  status: 'connected' | 'disconnected' | 'error' | 'unknown' | 'checking'
  message: string
  response_time: number
  tools: MCPTool[]
  
  // Built-in flag (default servers from mcp_client.py)
  is_builtin?: boolean
}