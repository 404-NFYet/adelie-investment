/**
 * API endpoints for Narrative Investment
 */

import { API_BASE_URL, fetchJson, postJson } from './client';

// Re-export module APIs
export { portfolioApi } from './portfolio';
export { narrativeApi } from './narrative';

export { authApi } from './auth';

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

// Keywords API
export const keywordsApi = {
  getToday: (date) =>
    fetch(`${API_BASE_URL}/api/v1/keywords/today${date ? `?date=${date}` : ''}`).then((r) => r.json()),
  getHistory: () =>
    fetch(`${API_BASE_URL}/api/v1/keywords/history`).then((r) => r.json()),
};

// Notification API
export const notificationApi = {
  getAll: (page = 1, perPage = 20) =>
    fetchJson(`${API_BASE_URL}/api/v1/notifications?page=${page}&per_page=${perPage}`),

  getUnreadCount: () =>
    fetchJson(`${API_BASE_URL}/api/v1/notifications/unread-count`),

  markAsRead: (notificationIds = null) =>
    postJson(`${API_BASE_URL}/api/v1/notifications/read`, { notification_ids: notificationIds }),
};

