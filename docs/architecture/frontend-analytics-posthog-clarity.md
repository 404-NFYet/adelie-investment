# 프론트 사용자 행동 로그 수집 가이드 (PostHog + Clarity)

## 1) 왜 이 조합을 쓰는가

우리 현재 목표는 아래 2개입니다.

1. 사용자가 어디서 막히는지 빠르게 본다. (세션 리플레이/히트맵)
2. 기능 단위 전환율을 정확히 본다. (이벤트/퍼널)

이 기준에서 가장 현실적인 조합은:

- `Microsoft Clarity`: 빠른 설치, 무료 세션 리플레이/히트맵
- `PostHog`: 이벤트 분석 + 퍼널 + 세션 리플레이 + 기능 플래그까지 확장 가능

즉, **Clarity로 빠른 관찰**, **PostHog로 제품 의사결정**이 핵심입니다.

---

## 2) PostHog / Clarity가 각각 뭔가

## PostHog

- 제품 분석 도구 (Product Analytics)
- 핵심 기능:
  - 이벤트 추적 (예: `ask_tutor_click`)
  - 퍼널 분석 (예: `narrative_view -> text_select -> tutor_send_success`)
  - 세션 리플레이
  - 코호트/리텐션
  - Feature Flag / 실험
- 장점:
  - 프론트 이벤트 설계와 운영이 쉬움
  - 개발팀이 직접 디버깅하기 좋음
- 단점:
  - 이벤트 설계를 안 하면 데이터가 금방 지저분해짐

## Clarity

- Microsoft의 사용자 행동 시각화 도구
- 핵심 기능:
  - 세션 리플레이
  - 히트맵
  - Rage click, dead click 같은 UX 시그널
- 장점:
  - 설치가 매우 간단
  - 비용 부담이 적음(대부분 무료 운영 가능)
- 단점:
  - 제품 퍼널 분석은 PostHog/Amplitude 계열보다 제한적

---

## 3) 우리 코드베이스 현재 상태

현재 이미 1차 분석 인프라는 있습니다.

- 프론트:
  - `frontend/src/utils/analytics.js`
  - `trackEvent`, `trackPageView` 구현
  - `/api/v1/analytics/events`로 배치 전송
- 백엔드:
  - `fastapi/app/api/routes/feedback.py`
  - `POST /feedback/analytics/events`에서 `usage_events` 저장

즉, **완전 신규 구축이 아니라, 외부 도구(PostHog/Clarity)를 병행 연동**하면 됩니다.

---

## 4) 권장 도입 방식 (우리 기준)

## 단계 A. 최소 도입 (1~2일)

목표: UI/UX 병목을 바로 보기

1. Clarity 설치
2. PostHog SDK 설치
3. 핵심 이벤트 8~12개만 우선 연결
4. 기존 `trackEvent` 유지 (백업 로그 역할)

## 단계 B. 운영 안정화 (3~5일)

목표: 팀이 매일 보는 지표 만들기

1. 이벤트 네이밍 규칙 확정
2. 퍼널/대시보드 생성
3. 개인정보 마스킹/동의 배너 정리
4. QA 환경/운영 환경 분리

## 단계 C. 고도화 (1~2주)

목표: 실험과 개선 루프 자동화

1. Feature Flag 연동
2. 코호트/리텐션 분석
3. 핵심 경로 이탈 알림(슬랙 등)

---

## 5) 실제 작업 항목 (파일 단위)

## 프론트엔드

1. SDK 설치

```bash
cd frontend
npm i posthog-js
```

2. 환경변수 추가 (`frontend/.env`, 배포 env)

```bash
VITE_POSTHOG_KEY=phc_xxx
VITE_POSTHOG_HOST=https://us.i.posthog.com
VITE_CLARITY_PROJECT_ID=xxxxxxx
VITE_ANALYTICS_ENABLED=true
```

3. Analytics bootstrap 파일 추가 (예시)
- 신규: `frontend/src/utils/analyticsProviders.js`
- 역할:
  - PostHog init
  - Clarity init (script 삽입)
  - 공통 `captureEvent(...)` 제공

4. 앱 시작 시 초기화
- 수정: `frontend/src/main.jsx`
- `initAnalytics()` 1회 호출

5. 기존 이벤트 함수와 통합
- 수정: `frontend/src/utils/analytics.js`
- `trackEvent` 내부에서:
  - 기존 `/api/v1/analytics/events` 전송 유지
  - 동시에 PostHog로 `capture`

6. 사용자 식별 연동
- 로그인 성공 시점(UserContext)에서:
  - `posthog.identify(user.id, { role, signup_date ... })`
- 로그아웃 시:
  - `posthog.reset()`

7. 페이지뷰 자동 추적
- 라우트 변경 시 `page_view` 이벤트를 PostHog에도 동일 전송

## 백엔드

1. 기존 `/feedback/analytics/events` 유지 (권장)
- 이유: 외부 도구 장애 시에도 내부 로그 보존

2. 옵션: 서버사이드 중요 이벤트 미러링
- 예: 결제, 주문, 핵심 트랜잭션은 서버에서도 PostHog API 전송

## 인프라/운영

1. 환경별 키 분리
- dev/stage/prod 각각 다른 PostHog project key

2. CSP 점검
- PostHog/Clarity 도메인 허용 필요

3. Ad-block 영향 모니터링
- 프론트 분석 도구 차단율이 일정 수준 존재함
- 핵심 이벤트는 서버 로그와 교차 검증

---

## 6) 이벤트 설계안 (우리 서비스 초안)

## 공통 속성

모든 이벤트에 공통으로 넣을 필드:

- `user_id` (가능 시)
- `session_id`
- `case_id`
- `route`
- `device_type` (`mobile|desktop`)
- `app_version` (배포 SHA 권장)

## 핵심 이벤트 (우선 12개)

1. `page_view`
2. `narrative_open`
3. `narrative_step_change`
4. `narrative_text_select`
5. `narrative_tutor_cta_show`
6. `narrative_tutor_cta_click`
7. `tutor_send_start`
8. `tutor_send_success`
9. `tutor_send_error`
10. `tutor_stream_stop`
11. `tutor_regenerate_click`
12. `glossary_open`

## 네이밍 규칙

- 과거형/수동형 대신 동사형 사용: `open`, `click`, `send_start`
- snake_case 고정
- 이벤트 이름은 최대한 짧고 의미 명확하게

---

## 7) 개인정보/보안 체크리스트

1. 절대 수집 금지
- 이름/이메일/전화번호 원문
- 자유입력 텍스트 원문(특히 튜터 질문 본문)

2. 선택 텍스트/질문은 원문 대신
- 길이 (`text_length`)
- 카테고리 (`topic=valuation|risk|term`)
- 해시(필요 시)만 저장

3. 마스킹
- Clarity 녹화 영역 중 민감 컴포넌트는 마스킹 처리

4. 동의 관리
- 쿠키/추적 동의 배너 정책에 맞춰 enable/disable
- `VITE_ANALYTICS_ENABLED` + 사용자 동의 상태 둘 다 확인

---

## 8) 구현 예시 코드 (요약)

```js
// frontend/src/utils/analyticsProviders.js
import posthog from 'posthog-js';

let initialized = false;

export function initAnalytics() {
  if (initialized || import.meta.env.VITE_ANALYTICS_ENABLED !== 'true') return;

  const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
  const posthogHost = import.meta.env.VITE_POSTHOG_HOST;
  if (posthogKey) {
    posthog.init(posthogKey, {
      api_host: posthogHost,
      capture_pageview: false,
      persistence: 'localStorage+cookie',
    });
  }

  const clarityId = import.meta.env.VITE_CLARITY_PROJECT_ID;
  if (clarityId && !window.clarity) {
    const s = document.createElement('script');
    s.async = true;
    s.src = `https://www.clarity.ms/tag/${clarityId}`;
    document.head.appendChild(s);
  }

  initialized = true;
}

export function captureEvent(name, props = {}) {
  if (import.meta.env.VITE_ANALYTICS_ENABLED !== 'true') return;
  try {
    posthog.capture(name, props);
  } catch {}
}
```

```js
// frontend/src/main.jsx
import { initAnalytics } from './utils/analyticsProviders';
initAnalytics();
```

```js
// frontend/src/utils/analytics.js 내부
import { captureEvent } from './analyticsProviders';

export function trackEvent(eventType, data = {}) {
  // 기존 내부 배치 로직 유지
  // ...
  captureEvent(eventType, data);
}
```

---

## 9) QA 시나리오

1. 로컬/dev에서 이벤트 발생 확인
- PostHog live events에서 `page_view` 확인

2. Narrative 핵심 플로우 검증
- 텍스트 선택 -> CTA 노출 -> CTA 클릭 -> 전송 성공
- 이벤트 순서가 누락 없이 찍히는지 확인

3. 오류 플로우 검증
- 전송 실패 시 `tutor_send_error` 기록 확인

4. 로그아웃 후 식별 초기화
- 다른 계정 로그인 시 사용자 오염 없는지 확인

5. 성능 체크
- Lighthouse/Performance에서 초기 로딩 영향 확인

---

## 10) 대시보드 초안

1. 퍼널
- `narrative_open -> narrative_text_select -> narrative_tutor_cta_click -> tutor_send_success`

2. 오류율
- `tutor_send_error / tutor_send_start`

3. 단계별 이탈
- `narrative_step_change` 이후 다음 step 미도달 비율

4. 디바이스 비교
- mobile vs desktop에서 `cta_click_rate` 비교

---

## 11) 운영 가이드 (현업 방식)

1. 주간 루틴
- PM/개발이 퍼널 이탈 상위 2개만 고른다
- 다음 주 배포에서 개선안 1~2개만 반영

2. 이벤트 변경 관리
- 이벤트 추가/수정은 PR 템플릿에 "Analytics impact" 항목 필수

3. 버전 태깅
- 배포 SHA를 이벤트 속성으로 보내서 전/후 비교

4. 도구 역할 분리
- Clarity: "무슨 일이 일어났나" 시각 확인
- PostHog: "어디서 얼마나 빠졌나" 정량 확인

---

## 12) 우리 프로젝트 기준 최종 권장안

1. 당장 시작
- Clarity 설치
- PostHog 설치
- 기존 `analytics.js` 유지

2. 이번 스프린트
- Narrative + Tutor 관련 핵심 이벤트 12개 연결
- 퍼널 대시보드 2개 생성

3. 다음 스프린트
- 동의/마스킹 정책 정리
- 서버 중요 이벤트 미러링

핵심 원칙은 **"빠르게 보되(Clarity), 결정은 이벤트로(PostHog)"** 입니다.

---

## 13) API 에러/소요시간 트래킹 (추가 요구사항 반영)

요청사항: "어느 API에서 에러가 나는지 + 소요시간까지 추적"

결론: 우리 프론트 구조에서는 `frontend/src/api/client.js` 한 곳에 계측을 넣는 방식이 가장 정확하고 유지보수에 유리합니다.

## 13.1 어디에 붙이면 되는가 (핵심)

공통 진입점:

- `authFetch(url, options, canRetry)`
- `fetchJson(url)`
- `postJson(url, body)`
- `deleteJson(url)`

이 4개를 타는 요청은 전체 자동 수집 가능.

즉, 대부분의 `/api/v1/*` 호출은 `client.js` 계층 계측만으로 커버됩니다.

## 13.2 이벤트 스키마 (API 전용)

권장 이벤트:

1. `api_request_success`
2. `api_request_error`
3. `api_request_timeout` (옵션)

공통 속성:

- `request_id`: 클라이언트 UUID
- `method`: `GET|POST|PUT|PATCH|DELETE`
- `endpoint`: 경로 템플릿(예: `/api/v1/tutor/sessions/:id/messages`)
- `status_code`: HTTP status (네트워크 오류면 `0`)
- `duration_ms`: 요청~응답(ms)
- `ok`: 성공 여부
- `network_error`: 네트워크/타임아웃 여부
- `retry_count`: 토큰 refresh 재시도 횟수
- `route`: 프론트 라우트
- `device_type`: `mobile|desktop`

## 13.3 구현 포인트 (client.js)

핵심은 `fetch` 전후 시간 측정 + 예외 경로에서 동일 스키마로 기록입니다.

```js
// frontend/src/api/client.js (개념 예시)
import { trackEvent } from '../utils/analytics';

const normalizeEndpoint = (url) => {
  try {
    const pathname = new URL(typeof url === 'string' ? url : url?.url, window.location.origin).pathname;
    return pathname
      .replace(/\/[0-9]+(?=\/|$)/g, '/:id')
      .replace(/\/[0-9a-fA-F-]{36}(?=\/|$)/g, '/:uuid');
  } catch {
    return 'unknown';
  }
};

const captureApiMetric = ({ url, method, statusCode, durationMs, errorMessage, retryCount = 0 }) => {
  const props = {
    method,
    endpoint: normalizeEndpoint(url),
    status_code: statusCode ?? 0,
    duration_ms: Math.round(durationMs),
    ok: statusCode >= 200 && statusCode < 400,
    network_error: !statusCode,
    retry_count: retryCount,
    route: window.location.pathname,
  };

  if (props.ok) {
    trackEvent('api_request_success', props);
  } else {
    trackEvent('api_request_error', {
      ...props,
      error_message: (errorMessage || '').slice(0, 200),
    });
  }
};
```

적용 순서:

1. `authFetch` 시작 시 `const startedAt = performance.now()`
2. 응답 받으면 `duration_ms` 계산 후 success/error 기록
3. throw/catch 경로도 동일하게 error 기록
4. refresh 후 재시도 시 `retry_count=1` 이상 기록

## 13.4 현재 코드 기준 "누락되는 fetch" 지점

아래는 공통 `client.js`를 타지 않는 raw `fetch` 사용 지점이라 API 추적 누락 가능성이 큽니다.

- `frontend/src/api/narrative.js`
- `frontend/src/api/auth.js` (일부)
- `frontend/src/pages/Portfolio.jsx` (일부)
- `frontend/src/components/domain/TermBottomSheet.jsx`
- `frontend/src/components/tutor/TutorPanel.jsx`
- `frontend/src/components/trading/StockSearch.jsx`
- `frontend/src/components/common/FeedbackWidget.jsx`
- `frontend/src/pages/Profile.jsx`
- `frontend/src/utils/analytics.js` (내부 analytics 전송 fetch)

권장 작업:

1. 1차: `client.js`에 계측 추가
2. 2차: 위 raw fetch를 `authFetch/fetchJson/postJson`로 점진 이관
3. 3차: 예외적으로 raw fetch가 필요하면 `trackedFetch` 래퍼 강제

## 13.5 대시보드 구성 (PostHog)

필수 차트:

1. `api_request_error` Top endpoint
2. endpoint별 `p50/p95 duration_ms`
3. `status_code` 분포 (401/403/429/500)
4. route별 오류율 (`api_request_error / (success+error)`)

알림 기준 예시:

- 특정 endpoint의 5분 오류율 > 3%
- 특정 endpoint의 p95 `duration_ms` > 2500ms

## 13.6 Clarity와 역할 분리

- PostHog: "어느 API가, 얼마나 느리고, 얼마나 실패하는지" 정량 분석
- Clarity: 해당 시간대 사용자 세션 리플레이로 UX 맥락 확인

즉, API 이슈는 PostHog 지표로 감지하고 Clarity로 사용자 체감 경로를 확인하는 방식이 운영 효율이 가장 좋습니다.

## 13.7 QA 체크리스트 (API 관측)

1. 정상 요청 시 `api_request_success` 기록
2. 4xx/5xx 시 `api_request_error` 기록
3. 네트워크 끊김 시 `status_code=0`, `network_error=true`
4. 동일 API 반복 호출에서 `duration_ms`가 합리적 범위로 누적
5. 토큰 만료 후 재시도 흐름에서 `retry_count` 반영
