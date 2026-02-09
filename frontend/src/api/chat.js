/**
 * chat.js - 채팅/용어 설명 API
 */
import { postJson } from './client';

export const explainTerm = (term, context = '') =>
  postJson('/api/v1/chat/explain', { term, context });
