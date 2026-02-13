/**
 * 공통 HTTP 클라이언트 설정 - 중앙 에러 핸들링 포함
 */
import { API_BASE_URL } from '../config';

export { API_BASE_URL };


/** localStorage에서 JWT 토큰을 읽어 Authorization 헤더를 생성 */
const getAuthHeaders = () => {
  const token = localStorage.getItem('token') || localStorage.getItem('authToken') || '';
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

/** JSON GET 요청 래퍼 (에러 핸들링 + 인증 헤더 포함) */
export const fetchJson = async (url) => {
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const msg = errorData.detail || errorData.message || `요청 실패 (${response.status})`;
    throw new Error(msg);
  }
  return response.json();
};

/** JSON POST 요청 래퍼 (에러 핸들링 + 인증 헤더 포함) */
export const postJson = async (url, body) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const msg = errorData.detail || errorData.message || `요청 실패 (${response.status})`;
    throw new Error(msg);
  }
  return response.json();
};
