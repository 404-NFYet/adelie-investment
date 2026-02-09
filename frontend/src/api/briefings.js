/**
 * briefings.js - 내러티브 브리핑 API (새 엔드포인트)
 */
import { fetchJson, postJson } from './client';

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

/**
 * 퀴즈 보상 처리
 * @param {object} data - { user_id, scenario_id, selected_answer, correct_answer }
 * @returns {Promise<{reward_amount: number, is_correct: boolean, new_cash_balance: number}>}
 */
export async function processQuizReward(data) {
  return postJson('/api/v1/quiz/reward', data);
}

export default { getLatestBriefing, listBriefings, getBriefingById, processQuizReward };
