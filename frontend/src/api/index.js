/**
 * API endpoints for Narrative Investment
 */

import { API_BASE_URL, fetchJson, postJson, deleteJson } from './client';

// Re-export module APIs
export { portfolioApi } from './portfolio';
export { narrativeApi } from './narrative';
export { learningApi } from './learning';

export { authApi } from './auth';

// Cases API
export const casesApi = {
  search: (query, recency = 'year', limit = 5) =>
    fetchJson(`${API_BASE_URL}/api/v1/search/cases?query=${encodeURIComponent(query)}&recency=${recency}&limit=${limit}`),

  getStory: (caseId, difficulty = 'beginner') =>
    fetchJson(`${API_BASE_URL}/api/v1/story/${caseId}?difficulty=${difficulty}`),

  getComparison: (caseId) =>
    fetchJson(`${API_BASE_URL}/api/v1/comparison/${caseId}`),

  getCompanies: (caseId) =>
    fetchJson(`${API_BASE_URL}/api/v1/companies/${caseId}`),
};

// Keywords API
export const keywordsApi = {
  getToday: (date) =>
    fetchJson(`${API_BASE_URL}/api/v1/keywords/today${date ? `?date=${date}` : ''}`),
  getHistory: () =>
    fetchJson(`${API_BASE_URL}/api/v1/keywords/history`),
};

// Notification API
export const notificationApi = {
  getAll: (page = 1, perPage = 20) =>
    fetchJson(`${API_BASE_URL}/api/v1/notifications?page=${page}&per_page=${perPage}`),

  getUnreadCount: () =>
    fetchJson(`${API_BASE_URL}/api/v1/notifications/unread-count`),

  markAsRead: (notificationIds = null) =>
    postJson(`${API_BASE_URL}/api/v1/notifications/read`, { notification_ids: notificationIds }),

  deleteOne: (notificationId) =>
    deleteJson(`${API_BASE_URL}/api/v1/notifications/${notificationId}`),

  deleteRead: () =>
    deleteJson(`${API_BASE_URL}/api/v1/notifications/read`),
};
