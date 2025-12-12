const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001/api';
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE || 'ws://localhost:8001/ws';

import { type MCPServerConfig } from './mcpConfig';

export interface Tool {
    name: string;
    description: string;
    functions?: string[];
    inputSchema?: any;
}

export interface ChatResponse {
    chat_id: string;
}

export const api = {
    getTools: async (config?: MCPServerConfig): Promise<Tool[]> => {
        const options: RequestInit = {};

        if (config) {
            options.method = 'POST';
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(config);
        } else {
            // Fallback or initial load without config
            options.method = 'POST'; // Changed to POST to match backend
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify({});
        }

        const response = await fetch(`${API_BASE}/tools`, options);
        if (!response.ok) {
            throw new Error('Failed to fetch tools');
        }
        return response.json();
    },

    createChat: async (message: string, mcpConfig?: MCPServerConfig): Promise<ChatResponse> => {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                mcp_config: mcpConfig  // Send config for tool fetching
            }),
        });
        return res.json();
    },

    getWebSocketUrl: (chatId: string) => `${WS_BASE}/chat/${chatId}`
};
