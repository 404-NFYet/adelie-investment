/**
 * briefings.js - 내러티브 브리핑 API (새 엔드포인트)
 */
import { fetchJson } from './client';

/**
 * 최신 브리핑 조회
 * @returns {Promise<object>} DailyNarrative with scenarios
 */
export async function getLatestBriefing() {
  return fetchJson('/api/v1/briefings/latest');
}

/**
 * 브리핑 목록 조회
 * @param {number} limit - 가져올 개수
 * @param {number} offset - 시작 위치
 * @returns {Promise<object[]>}
 */
export async function listBriefings(limit = 10, offset = 0) {
  return fetchJson(`/api/v1/briefings/list?limit=${limit}&offset=${offset}`);
}

/**
 * 특정 브리핑 조회
 * @param {string} id - 브리핑 ID (UUID)
 * @returns {Promise<object>}
 */
export async function getBriefingById(id) {
  return fetchJson(`/api/v1/briefings/${id}`);
}

export default { getLatestBriefing, listBriefings, getBriefingById };
