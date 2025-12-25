import { Skill } from '@/types/skill';
import { API_BASE, WS_BASE } from './data';

export interface ChatResponse {
    chat_id: string;
    session_id: string;
}

export const api = {
    createChat: async (
        message: string,
        fileUrls?: string[],
        fileNames?: string[],
        sessionId?: string
    ): Promise<ChatResponse> => {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                file_urls: fileUrls || [],  // Send file URLs
                file_names: fileNames || [],  // Send uploaded file names for Agent
                session_id: sessionId || null
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
