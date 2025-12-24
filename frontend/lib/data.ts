export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001/api'

export const AUTH_TOKEN_KEY = 'auth_token';

export const getAuthHeaders = (): HeadersInit => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
};