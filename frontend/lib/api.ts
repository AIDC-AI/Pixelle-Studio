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

import { Skill } from '@/types/skill';
import { Message } from '@/types/message';
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
    },

    // ==================== User Sessions API (cross-browser persistence) ====================

    /**
     * Get all sessions for a user from backend
     */
    getUserSessions: async (uid: number): Promise<Array<{
        session_id: string;
        title: string;
        uid: number;
        turn_count: number;
        created_at: string | null;
        updated_at: string | null;
    }>> => {
        const res = await fetch(`${API_BASE}/user-sessions?uid=${uid}`);
        if (!res.ok) {
            throw new Error('Failed to fetch user sessions');
        }
        return res.json();
    },

    /**
     * Get messages for a session from backend (reconstructed from turn/step data)
     */
    getSessionMessages: async (sessionId: string): Promise<{
        session_id: string;
        title: string | null;
        messages: Message[];
    }> => {
        const res = await fetch(`${API_BASE}/user-sessions/${sessionId}/messages`);
        if (!res.ok) {
            throw new Error('Failed to fetch session messages');
        }
        return res.json();
    },

    /**
     * Update session title on backend
     */
    updateSessionTitle: async (sessionId: string, title: string): Promise<void> => {
        const res = await fetch(`${API_BASE}/user-sessions/title`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, title }),
        });
        if (!res.ok) {
            console.error('Failed to save session title to backend');
        }
    },

    /**
     * Delete a session on backend
     */
    deleteUserSession: async (sessionId: string): Promise<void> => {
        const res = await fetch(`${API_BASE}/user-sessions/${sessionId}`, {
            method: 'DELETE',
        });
        if (!res.ok) {
            console.error('Failed to delete session from backend');
        }
    },
};
