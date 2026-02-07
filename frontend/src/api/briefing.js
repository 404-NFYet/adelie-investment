import { API_BASE_URL } from './client';

export const briefingApi = {
  getToday: (date) =>
    fetch(`${API_BASE_URL}/api/v1/briefing/today${date ? `?date=${date}` : ''}`).then(r => r.json()),
};
