/**
 * analyticsProviders.js - Clarity + PostHog SDK 래퍼
 *
 * 외부 분석 도구 통합 레이어. analytics.js에서 호출.
 * 모든 호출은 fire-and-forget + try/catch (분석이 앱을 깨뜨리면 안 됨)
 */

const CLARITY_ID = import.meta.env.VITE_CLARITY_ID || '';
const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || '';
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://analytics.adelie-invest.com';

let posthogInstance = null;
let clarityReady = false;

/**
 * Clarity SDK 초기화 (dynamic import)
 */
export async function initClarity() {
  if (!CLARITY_ID) return;
  try {
    const { default: Clarity } = await import('@microsoft/clarity');
    Clarity.init(CLARITY_ID);
    clarityReady = true;
  } catch (err) {
    console.warn('[Analytics] Clarity 초기화 실패:', err);
  }
}

/**
 * PostHog SDK 초기화
 */
export async function initPostHog() {
  if (!POSTHOG_KEY) return;
  try {
    const { default: posthog } = await import('posthog-js');
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      capture_pageview: false,   // SPA — 수동 페이지뷰
      autocapture: true,         // 클릭/폼 자동 수집
      persistence: 'localStorage',
    });
    posthogInstance = posthog;
  } catch (err) {
    console.warn('[Analytics] PostHog 초기화 실패:', err);
  }
}

/**
 * 유저 식별 (로그인 시)
 */
export function identifyUser(user) {
  if (!user?.id) return;
  try {
    if (clarityReady && window.clarity) {
      window.clarity('identify', String(user.id));
    }
  } catch {}
  try {
    if (posthogInstance) {
      posthogInstance.identify(String(user.id), {
        email: user.email || undefined,
        nickname: user.nickname || undefined,
      });
    }
  } catch {}
}

/**
 * 유저 리셋 (로그아웃 시)
 */
export function resetUser() {
  try {
    if (posthogInstance) {
      posthogInstance.reset();
    }
  } catch {}
}

/**
 * Clarity 커스텀 이벤트
 */
export function clarityEvent(eventType) {
  if (!clarityReady || !window.clarity) return;
  try {
    window.clarity('event', eventType);
  } catch {}
}

/**
 * PostHog 커스텀 이벤트
 */
export function posthogEvent(eventType, properties = {}) {
  if (!posthogInstance) return;
  try {
    posthogInstance.capture(eventType, properties);
  } catch {}
}

/**
 * Clarity 페이지뷰 (SPA 라우트 변경 시)
 */
export function clarityPageView() {
  if (!clarityReady || !window.clarity) return;
  try {
    // Clarity는 SPA 변경을 자동 감지하지만, 명시적 이벤트도 전송
    window.clarity('event', 'page_view');
  } catch {}
}

/**
 * PostHog 페이지뷰 (SPA 라우트 변경 시)
 */
export function posthogPageView() {
  if (!posthogInstance) return;
  try {
    posthogInstance.capture('$pageview');
  } catch {}
}
