# 분석 시스템 (Analytics)

## 개요
Clarity (MS 클라우드) + PostHog (셀프호스팅) + 자체 DB 저장 3중 구조.

## 아키텍처 — Bridge 패턴

```
컴포넌트 → trackEvent() → analytics.js
                              ├─ [1] POST /api/v1/analytics/events (자체 DB)
                              ├─ [2] window.clarity("event", ...) (Clarity)
                              └─ [3] posthog.capture(...)          (PostHog)
```

### 핵심 파일
| 파일 | 역할 |
|------|------|
| `frontend/src/utils/analytics.js` | 이벤트 허브 — trackEvent(), trackPageView() |
| `frontend/src/utils/analyticsProviders.js` | Clarity + PostHog SDK 래퍼 |
| `frontend/src/components/common/AnalyticsProvider.jsx` | SDK 초기화 + 유저 식별 + 자동 페이지뷰 |

## Clarity (세션 리플레이 + 히트맵)

- **서비스**: MS Clarity (클라우드, 무료 무제한)
- **대시보드**: [clarity.microsoft.com](https://clarity.microsoft.com) (Google SSO 로그인)
- **Project ID**: `vmrzbya185` (환경변수 `VITE_CLARITY_ID`)
- **수집 데이터**: 세션 리플레이, 클릭 히트맵, 스크롤 히트맵, 영역 히트맵
- **SDK**: `@microsoft/clarity` — dynamic import로 lazy load

## PostHog (퍼널 분석 + 이벤트)

- **서비스**: PostHog 셀프호스팅 (analytics LXD 서버)
- **대시보드**: [analytics.adelie-invest.com](https://analytics.adelie-invest.com)
- **API Key**: 환경변수 `VITE_POSTHOG_KEY` (`phc_xxx` 형식)
- **수집 데이터**: 퍼널 분석, 이벤트 분석, Feature Flags, 자동 캡처 (클릭, 폼)
- **SDK**: `posthog-js` — `analytics` 청크로 분리 (vite manualChunks)

### 주요 퍼널

| 퍼널 | 단계 |
|------|------|
| 온보딩 | Landing(`/`) → Auth(`/auth`) → login → Home(`/home`) |
| 콘텐츠 참여 | Home → keyword_click → Narrative → narrative_step(summary) |
| 매매 전환 | Narrative → narrative_step(application) → trade_execute |
| 튜터 활용 | 아무 페이지 → tutor_open → tutor_ask → 후속 질문 |

## 커스텀 이벤트 목록

| event_type | 설명 | data 스키마 |
|------------|------|------------|
| `page_view` | 페이지 진입 | `{ page }` |
| `page_duration` | 체류 시간 | `{ duration_sec }` |
| `keyword_click` | 키워드 카드 클릭 | `{ keyword_id, keyword_name }` |
| `narrative_step` | 내러티브 단계 진행 | `{ case_id, step }` |
| `trade_execute` | 모의매매 실행 | `{ stock_code, action, amount }` |
| `tutor_open` | 튜터 모달 열기 | `{}` |
| `tutor_ask` | 튜터 질문 | `{ message_length }` |
| `term_click` | 용어 클릭 | `{ term }` |
| `feedback_submit` | 피드백 제출 | `{ type, content }` |

## 새 이벤트 추가 방법

```javascript
import { trackEvent } from '../utils/analytics';

// 컴포넌트 내에서 호출만 하면 3개 서비스 자동 전달
trackEvent('new_event_type', { key: 'value' });
```

1. `trackEvent()` 호출 → analytics.js가 자체 DB + Clarity + PostHog에 동시 전달
2. PostHog 대시보드에서 자동으로 이벤트 확인 가능
3. Clarity에서는 커스텀 이벤트 기반 세션 필터링 가능

## 환경변수

| 변수명 | 로컬 개발 | 프로덕션 (deploy-test) | 설명 |
|--------|-----------|----------------------|------|
| `VITE_CLARITY_ID` | 빈 값 (수집 안 함) | `vmrzbya185` | Clarity Project ID |
| `VITE_POSTHOG_KEY` | 빈 값 (수집 안 함) | `phc_xxx` | PostHog API Key |
| `VITE_POSTHOG_HOST` | (기본값 사용) | `https://analytics.adelie-invest.com` | PostHog 서버 URL |

> 빈 값이면 SDK 초기화를 skip하므로 에러가 발생하지 않음.

## 트러블슈팅

### 광고 차단기
- uBlock Origin 등 광고 차단기가 Clarity/PostHog 요청을 차단할 수 있음
- 분석이 앱 동작에 영향을 주지 않도록 모든 호출이 try/catch로 래핑됨
- 자체 DB 수집 (`/api/v1/analytics/events`)은 동일 도메인이므로 차단되지 않음

### SDK 미로드
- `VITE_CLARITY_ID` 또는 `VITE_POSTHOG_KEY`가 빈 값이면 해당 SDK를 로드하지 않음
- 네트워크 탭에서 `clarity.ms.com` / `analytics.adelie-invest.com` 요청 확인
- 콘솔에서 `[Analytics]` 접두사 경고 메시지 확인

### PostHog 서버 접속 불가
- `analytics.adelie-invest.com` 접속 확인 → Cloudflare Tunnel 상태 확인
- analytics LXD 서버(10.10.10.17) Docker 상태 확인: `lxc exec analytics -- docker ps`
