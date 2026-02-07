/**
 * 공통 HTTP 클라이언트 설정 - 중앙 에러 핸들링 포함
 */
import { API_BASE_URL } from '../config';

export { API_BASE_URL };

export const SPRING_URL = import.meta.env.VITE_SPRING_URL || '';

/** JSON GET 요청 래퍼 (에러 핸들링 포함) */
export const fetchJson = async (url) => {
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const msg = errorData.detail || errorData.message || `요청 실패 (${response.status})`;
    throw new Error(msg);
  }
  return response.json();
};

/** JSON POST 요청 래퍼 (에러 핸들링 포함) */
export const postJson = async (url, body) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const msg = errorData.detail || errorData.message || `요청 실패 (${response.status})`;
    throw new Error(msg);
  }
  return response.json();
};
