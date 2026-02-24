// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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