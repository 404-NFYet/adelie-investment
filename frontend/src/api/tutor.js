import { API_BASE_URL } from './client';

export const tutorApi = {
  chat: async function* (message, sessionId, difficulty, contextType, contextId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/tutor/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message, session_id: sessionId, difficulty,
        context_type: contextType, context_id: contextId,
      }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          try { yield JSON.parse(line.slice(6)); } catch { /* 무시 */ }
        }
      }
    }
  },
};
