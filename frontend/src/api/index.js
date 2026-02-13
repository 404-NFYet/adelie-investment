/**
 * API endpoints for Narrative Investment
 */

import { API_BASE_URL } from '../config';

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

