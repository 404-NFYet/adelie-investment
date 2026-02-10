/**
 * briefing.js - 브리핑 API (client 래퍼 사용, 인증 헤더 자동 포함)
 */
import { fetchJson, postJson } from './client';

export const getLatestBriefing = () => fetchJson('/api/v1/briefings/latest');
export const listBriefings = (page = 1, size = 10) => fetchJson(`/api/v1/briefings/list?page=${page}&size=${size}`);
export const getBriefing = (id) => fetchJson(`/api/v1/briefings/${id}`);
