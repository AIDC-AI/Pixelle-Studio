export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001/api';
export const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE || 'ws://localhost:8001/ws';

import { Skill } from '@/types/skill';
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

    createChat: async (message: string, mcpConfig?: MCPServerConfig, fileUrls?: string[], filePaths?: string[]): Promise<ChatResponse> => {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                mcp_config: mcpConfig,  // Send config for tool fetching
                file_urls: fileUrls || [],  // Send file URLs
                file_paths: filePaths || []  // Send local file paths for Agent
            }),
        });
        return res.json();
    },

    getWebSocketUrl: (chatId: string) => `${WS_BASE}/chat/${chatId}`,

    getSkills: async (): Promise<Skill[]> =>  {
        const response = await fetch(`${API_BASE}/skills`);
        if (!response.ok) {
            throw new Error('Failed to fetch skills');
        }
        const data = await response.json();
        return data.skills;
    },

    getSkillContent: async (skillName: string) => {
        const response = await fetch(`${API_BASE}/skills/${skillName}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch skill detail: ${skillName}`);
        }
        const content = await response.json();
        return content
    },

    createSkill: async (name: string, content: string) => {
        const response = await fetch(`${API_BASE}/skills`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, content })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create skill');
        }
        return response.json();
    },

    updateSkill: async (skillName: string, content: string, newName?: string) => {
        const response = await fetch(`${API_BASE}/skills/${skillName}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, new_name: newName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update skill');
        }
        return response.json();
    },

    deleteSkill: async (skillName: string) => {
        const response = await fetch(`${API_BASE}/skills/${skillName}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete skill');
        }
        return response.json();
    }
};
