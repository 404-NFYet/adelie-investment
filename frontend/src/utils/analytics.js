/**
 * analytics.js - 사용 행동 분석 (자동 수집)
 * 데모 기간 중 UX 개선 데이터 확보
 */

let eventQueue = [];
let flushTimer = null;
const BATCH_SIZE = 10;
const FLUSH_INTERVAL = 5000; // 5초

/**
 * 세션 ID 생성/조회
 */
function getSessionId() {
  let sessionId = sessionStorage.getItem('adelie_session_id');
  if (!sessionId) {
    sessionId = crypto.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2);
    sessionStorage.setItem('adelie_session_id', sessionId);
  }
  return sessionId;
}

/**
 * 현재 사용자 ID (로그인 상태에 따라)
 */
function getCurrentUserId() {
  try {
    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      return user?.id || null;
    }
  } catch {}
  return null;
}

/**
 * 이벤트 추적
 * @param {string} eventType - page_view, narrative_step, trade_execute, tutor_ask, term_click, feedback_submit
 * @param {object} data - 추가 데이터
 */
export function trackEvent(eventType, data = {}) {
  const event = {
    user_id: getCurrentUserId(),
    session_id: getSessionId(),
    event_type: eventType,
    event_data: {
      ...data,
      timestamp: Date.now(),
      page: window.location.pathname,
    },
  };

  eventQueue.push(event);

  // 배치 사이즈 도달 시 즉시 전송
  if (eventQueue.length >= BATCH_SIZE) {
    flushEvents();
  }

  // 타이머 설정 (아직 없으면)
  if (!flushTimer) {
    flushTimer = setTimeout(flushEvents, FLUSH_INTERVAL);
  }
}

/**
 * 이벤트 배치 전송
 */
async function flushEvents() {
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }

  if (eventQueue.length === 0) return;

  const batch = [...eventQueue];
  eventQueue = [];

  try {
    await fetch('/api/v1/analytics/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: batch }),
    });
  } catch (err) {
    // 전송 실패 시 큐에 다시 추가 (최대 100개)
    eventQueue = [...batch, ...eventQueue].slice(0, 100);
    console.warn('Analytics 전송 실패:', err);
  }
}

/**
 * 페이지 체류 시간 추적 (자동)
 */
let pageEnterTime = Date.now();

export function trackPageView(pageName) {
  // 이전 페이지 체류 시간 기록
  const duration = Math.round((Date.now() - pageEnterTime) / 1000);
  if (duration > 1) {
    trackEvent('page_duration', { duration_sec: duration });
  }

  pageEnterTime = Date.now();
  trackEvent('page_view', { page: pageName });
}

/**
 * 페이지 이탈 시 이벤트 전송
 */
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', flushEvents);
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      flushEvents();
    }
  });
}
