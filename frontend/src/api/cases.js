import { API_BASE_URL } from './client';

export const casesApi = {
  search: (query, recency = 'year', limit = 5) =>
    fetch(`${API_BASE_URL}/api/v1/search/cases?query=${encodeURIComponent(query)}&recency=${recency}&limit=${limit}`).then(r => r.json()),
  getStory: (caseId, difficulty = 'beginner') =>
    fetch(`${API_BASE_URL}/api/v1/story/${caseId}?difficulty=${difficulty}`).then(r => r.json()),
  getComparison: (caseId) =>
    fetch(`${API_BASE_URL}/api/v1/comparison/${caseId}`).then(r => r.json()),
  getCompanies: (caseId) =>
    fetch(`${API_BASE_URL}/api/v1/companies/${caseId}`).then(r => r.json()),
};
