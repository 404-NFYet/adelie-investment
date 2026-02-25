/**
 * 공통 HTTP 클라이언트 설정 - 중앙 에러 핸들링 포함
 */
import { API_BASE_URL } from '../config';

export { API_BASE_URL };

const AUTH_BYPASS_PATHS = [
  '/api/v1/auth/login',
  '/api/v1/auth/register',
  '/api/v1/auth/refresh',
];

let refreshPromise = null;

const toPathname = (url) => {
  try {
    const value = typeof url === 'string' ? url : url?.url;
    if (!value) return '';
    return new URL(value, window.location.origin).pathname;
  } catch {
    return '';
  }
};

const isAuthBypassRequest = (url) => {
  const pathname = toPathname(url);
  return AUTH_BYPASS_PATHS.some((path) => pathname.endsWith(path));
};

/** CSRF 토큰 쿠키 읽기 (Double-Submit Cookie 패턴) */
const getCsrfToken = () => {
  const match = document.cookie.match(/(?:^|;\s*)csrfToken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
};

/** 요청 헤더 생성: POST/PUT/PATCH/DELETE 시 CSRF 토큰 포함 */
const mergeHeaders = (headers, method) => {
  const merged = new Headers(headers || {});
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method?.toUpperCase())) {
    const csrf = getCsrfToken();
    if (csrf) merged.set('X-CSRF-Token', csrf);
  }
  return merged;
};

/** 인증 실패 시 자동 로그아웃 이벤트 발행 + 로그인 화면 이동 */
const handleAuthFailure = () => {
  window.dispatchEvent(new Event('auth:logout'));
  if (!window.location.pathname.startsWith('/auth')) {
    window.location.assign('/auth');
  }
};

const readErrorMessage = async (response) => {
  const errorData = await response.json().catch(() => ({}));
  return errorData.detail || errorData.message || `요청 실패 (${response.status})`;
};

/** 리프레시 토큰으로 액세스 토큰 갱신 (쿠키 자동 전송) */
const refreshAccessToken = async () => {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      const message = await readErrorMessage(response);
      throw new Error(message);
    }
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
};

/** 인증 포함 fetch (HttpOnly 쿠키 자동 전송, 401 시 refresh 후 1회 재시도) */
export const authFetch = async (url, options = {}, canRetry = true) => {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: mergeHeaders(options.headers, options.method),
  });

  if (response.status !== 401 || !canRetry || isAuthBypassRequest(url)) {
    return response;
  }

  try {
    await refreshAccessToken();
    const retried = await fetch(url, {
      ...options,
      credentials: 'include',
      headers: mergeHeaders(options.headers, options.method),
    });
    if (retried.status === 401) {
      handleAuthFailure();
    }
    return retried;
  } catch (error) {
    handleAuthFailure();
    throw error;
  }
};

/** JSON GET 요청 래퍼 (에러 핸들링 + 인증 헤더 포함) */
export const fetchJson = async (url) => {
  const response = await authFetch(url);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json();
};

/** JSON POST 요청 래퍼 (에러 핸들링 + 인증 헤더 포함) */
export const postJson = async (url, body) => {
  const response = await authFetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json();
};

/** JSON DELETE 요청 래퍼 (에러 핸들링 + 인증 헤더 포함) */
export const deleteJson = async (url) => {
  const response = await authFetch(url, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json();
};
