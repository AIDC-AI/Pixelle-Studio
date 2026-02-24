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

import { UserResponse, CreateUserRequest, UpdateUserRequest, Token } from '@/types/user';
import { API_BASE, AUTH_TOKEN_KEY, getAuthHeaders } from './data';
 
export const userAPI = {
    // Store token
    setToken(token: string) {
        localStorage.setItem(AUTH_TOKEN_KEY, token);
    },

    // Get token
    getToken(): string | null {
        return localStorage.getItem(AUTH_TOKEN_KEY);
    },

    // Remove token
    clearToken() {
        localStorage.removeItem(AUTH_TOKEN_KEY);
    },

    // Check if authenticated
    isAuthenticated(): boolean {
        return !!localStorage.getItem(AUTH_TOKEN_KEY);
    },

    // Get current user
    async getCurrentUser(): Promise<UserResponse> {
        const response = await fetch(`${API_BASE}/users/me`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error('Failed to fetch current user');
        }
        return response.json();
    },

    // Get all users
    async getUsers(): Promise<UserResponse[]> {
        const response = await fetch(`${API_BASE}/users`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error('Failed to fetch users');
        }
        return response.json();
    },

    // Get a single user
    async getUser(uid: number): Promise<UserResponse> {
        const response = await fetch(`${API_BASE}/users/${uid}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error('Failed to fetch user');
        }
        return response.json();
    },

    // Create user
    async createUser(user: CreateUserRequest): Promise<UserResponse> {
        const response = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(user)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create user');
        }
        return response.json();
    },

    // Update user
    async updateUser(uid: number, user: UpdateUserRequest): Promise<UserResponse> {
        const response = await fetch(`${API_BASE}/users/${uid}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(user)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'Failed to update user');
        }
        return response.json();
    },

    // Delete user
    async deleteUser(uid: number): Promise<void> {
        const response = await fetch(`${API_BASE}/users/${uid}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'Failed to delete user');
        }
    },

    // Login
    async login(email: string, password: string): Promise<{ message: string; user: UserResponse, token: Token }> {
        const response = await fetch(`${API_BASE}/users/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'Login failed');
        }
        const data = await response.json();
        // Store token after successful login
        this.setToken(data.token.access_token);
        return data;
    },

    // Logout
    logout() {
        this.clearToken();
    }
};
