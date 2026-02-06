/**
 * 공통 HTTP 클라이언트 설정
 */
import { API_BASE_URL } from '../config';

export { API_BASE_URL };

export const SPRING_URL = import.meta.env.VITE_SPRING_URL || '';

/** JSON GET 요청 래퍼 */
export const fetchJson = (url) => fetch(url).then((r) => r.json());

/** JSON POST 요청 래퍼 */
export const postJson = (url, body) =>
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((r) => r.json());
