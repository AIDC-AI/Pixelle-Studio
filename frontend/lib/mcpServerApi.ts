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
    tools: MCPTool[];  // 添加 tools 字段
}

export const mcpServerAPI = {
    // 获取所有服务器（包含状态和工具）
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

    // 获取单个服务器
    async getServer(id: string): Promise<MCPServer> {
        const response = await fetch(`${API_BASE}/mcp-servers/${id}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error('Failed to fetch server');
        }
        return response.json();
    },

    // 检查服务器连接状态（包含工具列表）
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

    // 获取服务器的工具列表（已废弃，使用 checkServerStatus 代替）
    // @deprecated Use checkServerStatus instead
    async getServerTools(serverId: string): Promise<ToolsResponse> {
        // 调用 status 接口获取工具
        const status = await this.checkServerStatus(serverId);
        return {
            tools: status.tools,
            server_id: status.server_id,
            server_name: status.server_name
        };
    },

    // 创建服务器
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

    // 更新服务器
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

    // 删除服务器
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

