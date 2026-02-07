import { API_BASE_URL } from './client';

export const narrativeApi = {
  getNarrative: (caseId, difficulty = 'beginner') =>
    fetch(`${API_BASE_URL}/api/v1/narrative/${caseId}?difficulty=${difficulty}`).then(r => {
      if (!r.ok) throw new Error(`Narrative API error: ${r.status}`);
      return r.json();
    }),
};
