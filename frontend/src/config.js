/**
 * Application configuration
 * API Base URL을 한 곳에서 관리
 */
// 프로덕션: 빈 문자열 -> nginx 프록시 통해 요청 / 개발: VITE_FASTAPI_URL 설정
export const API_BASE_URL = import.meta.env.VITE_FASTAPI_URL || import.meta.env.VITE_API_URL || '';
