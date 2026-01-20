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
  // 获取所有技能
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

  // 获取单个技能详情
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

  // 创建技能
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

  // 更新技能
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

  // 删除技能
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
