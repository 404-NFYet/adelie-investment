import { SPRING_URL } from './client';

export const authApi = {
  login: (email, password) =>
    fetch(`${SPRING_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }).then(r => { if (!r.ok) throw new Error('Login failed'); return r.json(); }),

  register: (email, password, username) =>
    fetch(`${SPRING_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username }),
    }).then(r => { if (!r.ok) throw new Error('Registration failed'); return r.json(); }),

  getMe: (token) =>
    fetch(`${SPRING_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => { if (!r.ok) throw new Error('Auth check failed'); return r.json(); }),
};
