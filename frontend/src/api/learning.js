import { API_BASE_URL, fetchJson, postJson } from './client';

export const learningApi = {
  getProgress: ({ contentType, status } = {}) => {
    const params = new URLSearchParams();
    if (contentType) params.set('content_type', contentType);
    if (status) params.set('status', status);
    const query = params.toString();
    return fetchJson(`${API_BASE_URL}/api/v1/learning/progress${query ? `?${query}` : ''}`);
  },

  upsertProgress: (payload) =>
    postJson(`${API_BASE_URL}/api/v1/learning/progress`, payload),
};
