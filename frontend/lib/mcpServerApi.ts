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

import { MCPServer, MCPTool } from '@/types/server';
import { API_BASE, getAuthHeaders } from './data';

export interface ToolsResponse {
    tools: MCPTool[];
    server_id: string;
    server_name: string;
}

export interface ConnectionStatus {
    server_id: string;
    server_name: string;
    status: 'connected' | 'disconnected' | 'error';
    message: string;
    response_time: number;
    tools: MCPTool[];  // Added tools field
}

export const mcpServerAPI = {
    // Get all servers (including status and tools)
    async getServers(checkStatus: boolean = true): Promise<MCPServer[]> {
        const url = checkStatus 
            ? `${API_BASE}/mcp-servers?check_status=true`
            : `${API_BASE}/mcp-servers?check_status=false`;
            
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error('Failed to fetch servers');
        }
        return response.json();
    },

    // Get a single server
    async getServer(id: string): Promise<MCPServer> {
        const response = await fetch(`${API_BASE}/mcp-servers/${id}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error('Failed to fetch server');
        }
        return response.json();
    },

    // Check server connection status (includes tool list)
    async checkServerStatus(serverId: string): Promise<ConnectionStatus> {
        const response = await fetch(`${API_BASE}/mcp-servers/${serverId}/status`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to check server status');
        }
        return response.json();
    },

    // Create server
    async createServer(server: Omit<MCPServer, 'id' | 'uid' | 'created_at' | 'updated_at'>): Promise<MCPServer> {
        const response = await fetch(`${API_BASE}/mcp-servers`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(server)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'Failed to create server');
        }
        return response.json();
    },

    // Update server
    async updateServer(id: string, server: Partial<Omit<MCPServer, 'id' | 'uid' | 'created_at' | 'updated_at'>>): Promise<MCPServer> {
        const response = await fetch(`${API_BASE}/mcp-servers/${id}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(server)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'Failed to update server');
        }
        return response.json();
    },

    // Delete server
    async deleteServer(id: string): Promise<void> {
        const response = await fetch(`${API_BASE}/mcp-servers/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'Failed to delete server');
        }
    }
};

