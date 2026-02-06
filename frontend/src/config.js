/**
 * Application configuration
 * API Base URL을 한 곳에서 관리
 */
export const API_BASE_URL = import.meta.env.VITE_FASTAPI_URL || import.meta.env.VITE_API_URL || 'http://localhost:8082';
