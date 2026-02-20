const API_BASE = import.meta.env.VITE_NEWS_API_BASE || 'http://localhost:8091';

function parseErrorMessage(data, status) {
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.detail?.message === 'string') {
    const code = data?.detail?.code ? `[${data.detail.code}] ` : '';
    return `${code}${data.detail.message}`;
  }
  if (typeof data?.message === 'string') return data.message;
  return `요청 실패 (${status})`;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(parseErrorMessage(data, res.status));
  }
  return data;
}

export const newsApi = {
  health: () => request('/api/news/health'),
  sources: (market) => request(`/api/news/sources?market=${market}`),
  headlines: ({ market, sourceId, limit = 20 }) => {
    const params = new URLSearchParams({ market, limit: String(limit) });
    if (sourceId) params.set('source_id', sourceId);
    return request(`/api/news/headlines?${params.toString()}`);
  },
  analyze: ({ url, difficulty, market }) =>
    request('/api/news/analyze', {
      method: 'POST',
      body: JSON.stringify({ url, difficulty, market }),
    }),
  visualize: ({ description, dataContext }) =>
    request('/api/news/visualize', {
      method: 'POST',
      body: JSON.stringify({ description, data_context: dataContext }),
    }),
  explainTerm: ({ term, difficulty }) => {
    const params = new URLSearchParams({ term, difficulty });
    return request(`/api/news/explain-term?${params.toString()}`);
  },
};
