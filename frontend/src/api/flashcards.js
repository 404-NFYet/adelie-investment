/**
 * 복습카드 API 클라이언트
 */
import { fetchJson, postJson, deleteJson, API_BASE_URL } from './client';

const BASE = `${API_BASE_URL}/api/v1/flashcards`;

/**
 * 복습카드 저장
 * @param {{ title: string, content_html: string, source_session_id?: number }} body
 */
export const saveFlashCard = (body) => postJson(BASE, body);

/**
 * 복습카드 목록 조회 (최신순)
 */
export const listFlashCards = () => fetchJson(BASE);

/**
 * 복습카드 삭제
 * @param {number} id
 */
export const deleteFlashCard = (id) => deleteJson(`${BASE}/${id}`);
