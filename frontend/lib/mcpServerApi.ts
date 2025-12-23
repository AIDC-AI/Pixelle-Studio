import { MCPServer } from '@/types/server';

const API_BASE = '/api';

export const mcpServerAPI = {
    // 获取所有服务器
    async getServers(): Promise<MCPServer[]> {
        const response = await fetch(`${API_BASE}/mcp-servers`);
        if (!response.ok) {
            throw new Error('Failed to fetch servers');
        }
        const data = await response.json();
        return data.servers;
    },

    // 获取单个服务器
    async getServer(id: string): Promise<MCPServer> {
        const response = await fetch(`${API_BASE}/mcp-servers/${id}`);
        if (!response.ok) {
            throw new Error('Failed to fetch server');
        }
        return response.json();
    },

    // 创建服务器
    async createServer(server: Omit<MCPServer, 'id'>): Promise<MCPServer> {
        const response = await fetch(`${API_BASE}/mcp-servers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(server)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create server');
        }
        return response.json();
    },

    // 更新服务器
    async updateServer(id: string, server: Partial<Omit<MCPServer, 'id'>>): Promise<MCPServer> {
        const response = await fetch(`${API_BASE}/mcp-servers/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(server)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update server');
        }
        return response.json();
    },

    // 删除服务器
    async deleteServer(id: string): Promise<void> {
        const response = await fetch(`${API_BASE}/mcp-servers/${id}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete server');
        }
    }
};
