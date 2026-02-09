import { Skill, SkillMeta } from '@/types/skill';
import { API_BASE, getAuthHeaders } from './data';

export interface CreateSkillRequest {
  name: string;
  description: string;
  content: string;
}

export interface UpdateSkillRequest {
  description: string;
  content: string;
}

export interface SkillOperationResponse {
  success: boolean;
  name: string;
  path: string;
  scope: string;
  message?: string;
}

export const skillAPI = {
  // Get all skills
  async getSkills(userId?: number): Promise<SkillMeta[]> {
    const url = userId 
      ? `${API_BASE}/skills?user_id=${userId}`
      : `${API_BASE}/skills`;
      
    const response = await fetch(url, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error('Failed to fetch skills');
    }
    const data = await response.json();
    return data.skills;
  },

  // Get a single skill detail
  async getSkill(skillName: string, userId?: number): Promise<Skill> {
    const url = userId
      ? `${API_BASE}/skills/${encodeURIComponent(skillName)}?user_id=${userId}`
      : `${API_BASE}/skills/${encodeURIComponent(skillName)}`;
      
    const response = await fetch(url, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch skill');
    }
    return response.json();
  },

  // Create skill
  async createSkill(request: CreateSkillRequest, userId?: number): Promise<SkillOperationResponse> {
    const url = userId
      ? `${API_BASE}/skills?user_id=${userId}`
      : `${API_BASE}/skills`;
      
    const response = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create skill');
    }
    return response.json();
  },

  // Update skill
  async updateSkill(
    skillName: string, 
    request: UpdateSkillRequest, 
    userId?: number
  ): Promise<SkillOperationResponse> {
    const url = userId
      ? `${API_BASE}/skills/${encodeURIComponent(skillName)}?user_id=${userId}`
      : `${API_BASE}/skills/${encodeURIComponent(skillName)}`;
      
    const response = await fetch(url, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update skill');
    }
    return response.json();
  },

  // Delete skill
  async deleteSkill(skillName: string, userId?: number): Promise<SkillOperationResponse> {
    const url = userId
      ? `${API_BASE}/skills/${encodeURIComponent(skillName)}?user_id=${userId}`
      : `${API_BASE}/skills/${encodeURIComponent(skillName)}`;
      
    const response = await fetch(url, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete skill');
    }
    return response.json();
  }
};
