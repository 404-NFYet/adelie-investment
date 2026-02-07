/**
 * API endpoints for Narrative Investment
 */

import { API_BASE_URL } from '../config';

// Re-export module APIs
export { portfolioApi } from './portfolio';
export { narrativeApi } from './narrative';

// Auth API (Spring Boot)
// 프로덕션에서는 빈 문자열 -> nginx 프록시를 통해 요청
const SPRING_URL = import.meta.env.VITE_SPRING_URL || '';

export const authApi = {
  login: (email, password) =>
    fetch(`${SPRING_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }).then(async r => {
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        throw new Error(data.message || '로그인에 실패했습니다');
      }
      return r.json();
    }),

  register: (email, password, username) =>
    fetch(`${SPRING_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username }),
    }).then(async r => {
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        // Spring Boot validation 에러 메시지 추출
        const msg = data.errors?.[0]?.defaultMessage || data.message || '회원가입에 실패했습니다';
        throw new Error(msg);
      }
      return r.json();
    }),

  getMe: (token) =>
    fetch(`${SPRING_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => {
      if (!r.ok) throw new Error('Auth check failed');
      return r.json();
    }),
};

// Briefing API
export const briefingApi = {
  getToday: (date) =>
    fetch(`${API_BASE_URL}/api/v1/briefing/today${date ? `?date=${date}` : ''}`).then((r) =>
      r.json()
    ),
};

// Cases API
export const casesApi = {
  search: (query, recency = 'year', limit = 5) =>
    fetch(
      `${API_BASE_URL}/api/v1/search/cases?query=${encodeURIComponent(query)}&recency=${recency}&limit=${limit}`
    ).then((r) => r.json()),

  getStory: (caseId, difficulty = 'beginner') =>
    fetch(`${API_BASE_URL}/api/v1/story/${caseId}?difficulty=${difficulty}`).then((r) =>
      r.json()
    ),

  getComparison: (caseId) =>
    fetch(`${API_BASE_URL}/api/v1/comparison/${caseId}`).then((r) => r.json()),

  getCompanies: (caseId) =>
    fetch(`${API_BASE_URL}/api/v1/companies/${caseId}`).then((r) => r.json()),
};

// Glossary API
export const glossaryApi = {
  getAll: (params = {}) => {
    const url = new URL(`${API_BASE_URL}/api/v1/glossary`);
    Object.entries(params).forEach(([key, value]) => {
      if (value) url.searchParams.append(key, value);
    });
    return fetch(url).then((r) => r.json());
  },

  getById: (termId) =>
    fetch(`${API_BASE_URL}/api/v1/glossary/${termId}`).then((r) => r.json()),

  searchByTerm: (term) =>
    fetch(`${API_BASE_URL}/api/v1/glossary/search/${encodeURIComponent(term)}`).then((r) =>
      r.json()
    ),
};

// Pipeline API
export const pipelineApi = {
  trigger: (tasks, date) =>
    fetch(`${API_BASE_URL}/api/v1/pipeline/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tasks, date }),
    }).then((r) => r.json()),

  getStatus: (jobId) =>
    fetch(`${API_BASE_URL}/api/v1/pipeline/status/${jobId}`).then((r) => r.json()),
};

// Keywords API
export const keywordsApi = {
  getToday: (date) =>
    fetch(`${API_BASE_URL}/api/v1/keywords/today${date ? `?date=${date}` : ''}`).then((r) => r.json()),
  getHistory: () =>
    fetch(`${API_BASE_URL}/api/v1/keywords/history`).then((r) => r.json()),
};

// Notification API
export const notificationApi = {
  getAll: (userId, page = 1, perPage = 20) =>
    fetch(`${API_BASE_URL}/api/v1/notifications/${userId}?page=${page}&per_page=${perPage}`).then(r => r.json()),

  getUnreadCount: (userId) =>
    fetch(`${API_BASE_URL}/api/v1/notifications/${userId}/unread-count`).then(r => r.json()),

  markAsRead: (userId, notificationIds = null) =>
    fetch(`${API_BASE_URL}/api/v1/notifications/${userId}/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notification_ids: notificationIds }),
    }).then(r => r.json()),
};

// Tutor API (SSE streaming)
export const tutorApi = {
  chat: async function* (message, sessionId, difficulty, contextType, contextId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/tutor/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        difficulty,
        context_type: contextType,
        context_id: contextId,
      }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            yield JSON.parse(line.slice(6));
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  },
};
