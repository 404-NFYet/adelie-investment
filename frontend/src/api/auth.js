import { API_BASE_URL, postJson, authFetch } from './client';

export const authApi = {
  login: (email, password) =>
    postJson(`${API_BASE_URL}/api/v1/auth/login`, { email, password }),

  register: (email, password, username) =>
    postJson(`${API_BASE_URL}/api/v1/auth/register`, { email, password, username }),

  getMe: async (token) => {
    const response = await authFetch(`${API_BASE_URL}/api/v1/auth/me`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) throw new Error('Auth check failed');
    return response.json();
  },
};
