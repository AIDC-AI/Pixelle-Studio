import { Skill } from '@/types/skill';
import { API_BASE, WS_BASE } from './data';

export interface ChatResponse {
    chat_id: string;
    session_id: string;
}

export interface GenerateTitleResponse {
    title: string;
}

export const api = {
    generateTitle: async (message: string): Promise<GenerateTitleResponse> => {
        const res = await fetch(`${API_BASE}/generate-title`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        return res.json();
    },

    createChat: async (
        message: string,
        userId: number,
        fileUrls?: string[],
        fileNames?: string[],
        sessionId?: string,
    ): Promise<ChatResponse> => {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                file_urls: fileUrls || [],  // Send file URLs
                file_names: fileNames || [],  // Send uploaded file names for Agent
                session_id: sessionId || null,
                user_id: userId
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
