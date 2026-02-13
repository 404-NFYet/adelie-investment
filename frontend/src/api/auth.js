import { API_BASE_URL, postJson, fetchJson } from './client';

export const authApi = {
  login: (email, password) =>
    postJson(`${API_BASE_URL}/api/v1/auth/login`, { email, password }),

  register: (email, password, username) =>
    postJson(`${API_BASE_URL}/api/v1/auth/register`, { email, password, username }),

  getMe: (token) =>
    fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(async r => {
      if (!r.ok) throw new Error('Auth check failed');
      return r.json();
    }),
};
