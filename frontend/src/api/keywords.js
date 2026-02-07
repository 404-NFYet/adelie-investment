import { API_BASE_URL } from './client';

export const keywordsApi = {
  getToday: (date) =>
    fetch(`${API_BASE_URL}/api/v1/keywords/today${date ? `?date=${date}` : ''}`).then(r => r.json()),
  getHistory: () =>
    fetch(`${API_BASE_URL}/api/v1/keywords/history`).then(r => r.json()),
  getPopular: (limit = 5) =>
    fetch(`${API_BASE_URL}/api/v1/keywords/popular?limit=${limit}`).then(r => r.json()),
  getRecentCases: (limit = 5) =>
    fetch(`${API_BASE_URL}/api/v1/keywords/recent-cases?limit=${limit}`).then(r => r.json()),
};
