/**
 * formatNumber.js - 숫자 포맷팅 유틸리티
 * 한국어 원화/거래량 등 포맷 통합
 */

/** 원화 포맷: 1234567 → "1,234,567원" */
export function formatKRW(value) {
  return new Intl.NumberFormat('ko-KR').format(Math.round(value)) + '원';
}

/** 거래량 포맷: 큰 숫자 한국어 단위 */
export function formatVolume(value) {
  if (!value && value !== 0) return '0';
  const num = Number(value);
  if (num >= 100000000) return (num / 100000000).toFixed(1).replace(/\.0$/, '') + '억';
  if (num >= 10000) return Math.round(num / 10000).toLocaleString('ko-KR') + '만';
  return num.toLocaleString('ko-KR');
}

/** 컴팩트 포맷: 억/만 단위 자동 변환 */
export function formatCompact(value) {
  if (!value && value !== 0) return '0';
  const num = Number(value);
  if (num >= 100000000) return (num / 100000000).toFixed(1).replace(/\.0$/, '') + '억';
  if (num >= 10000) return (num / 10000).toFixed(1).replace(/\.0$/, '') + '만';
  return num.toLocaleString('ko-KR');
}
