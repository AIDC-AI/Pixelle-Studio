export interface MCPToolInputSchema {
    type?: string;
    properties?: Record<string, {
        type?: string;
        description?: string;
    }>;
    required?: string[];
}

export interface MCPTool {
    name: string;
    description: string;
    inputSchema?: MCPToolInputSchema | any;
    outputSchema?: any;
    server_id?: string;
    server_url?: string;
    server_type?: string;
    server_name?: string;
}

export interface MCPServer {
  id: string
  name: string
  transport: 'streamable-http' | 'sse' | 'stdio'
  url?: string | null
  command?: string | null
  args?: string | null
  error?: string | null
  uid: string
  created_at: string
  updated_at: string
  
  // 状态信息（从后端返回）
  status: 'connected' | 'disconnected' | 'error' | 'unknown' | 'checking'
  message: string
  response_time: number
  tools: MCPTool[]
}