/**
 * chat.js - 채팅/용어 설명 API
 */
import { postJson } from './client';

/**
 * 용어 설명 요청
 * @param {string} term - 설명할 용어
 * @param {string} context - 용어가 사용된 맥락 (선택)
 * @returns {Promise<{term: string, explanation: string}>}
 */
export async function explainTerm(term, context = '') {
  return postJson('/api/v1/chat/explain', { term, context });
}

export default { explainTerm };
