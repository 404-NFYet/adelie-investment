/**
 * Canvas Engine API 클라이언트
 * @module api/canvas
 *
 * 모든 엔드포인트가 /api/v1/agent/* 통합 라우터를 사용한다.
 */

import { authFetch, fetchJson, postJson } from './client';

/**
 * Canvas 분석 SSE 스트리밍 요청
 * @deprecated analyzeCanvas는 현재 프론트에서 미사용. 향후 제거 예정.
 * @param {Object} payload - CanvasAnalyzeRequest
 * @param {AbortSignal} [signal] - AbortController signal
 * @returns {Promise<Response>} SSE Response (body is ReadableStream)
 */
export async function analyzeCanvas(payload, signal) {
  return authFetch('/api/v1/agent/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });
}

/**
 * 사전 연산된 Canvas 데이터 조회
 * @param {string} [mode='home']
 * @param {string} [date] - YYYY-MM-DD
 * @returns {Promise<Object>} CanvasPrecomputedResponse
 */
export async function getPrecomputed(mode = 'home', date) {
  const params = new URLSearchParams({ mode });
  if (date) params.set('date', date);
  return fetchJson(`/api/v1/agent/precomputed?${params}`);
}

/**
 * Quick QA — 드래그 선택 즉석 설명
 * @param {Object} payload - { selected_text, canvas_context_summary?, session_id? }
 * @returns {Promise<Object>} QuickQAResponse
 */
export async function quickQA(payload) {
  return postJson('/api/v1/agent/quick-qa', payload);
}

/**
 * CTA 피드백 전송 (fire-and-forget)
 * @param {Object} payload - CTAFeedbackRequest
 */
export function sendCTAFeedback(payload) {
  const url = '/api/v1/agent/cta-feedback';
  // sendBeacon for unload, fetch otherwise
  if (navigator.sendBeacon && payload.action === 'ignored') {
    navigator.sendBeacon(
      url,
      new Blob([JSON.stringify(payload)], { type: 'application/json' }),
    );
  } else {
    postJson(url, payload).catch(() => {});
  }
}
