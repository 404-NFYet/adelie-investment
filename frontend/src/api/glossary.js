import { API_BASE_URL } from './client';

export const glossaryApi = {
  getAll: (params = {}) => {
    const url = new URL(`${API_BASE_URL}/api/v1/glossary`, window.location.origin);
    Object.entries(params).forEach(([key, value]) => { if (value) url.searchParams.append(key, value); });
    return fetch(url).then(r => r.json());
  },
  getById: (termId) =>
    fetch(`${API_BASE_URL}/api/v1/glossary/${termId}`).then(r => r.json()),
  searchByTerm: (term) =>
    fetch(`${API_BASE_URL}/api/v1/glossary/search/${encodeURIComponent(term)}`).then(r => r.json()),
};
