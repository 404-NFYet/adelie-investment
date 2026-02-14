# Frontend 아키텍처

## 기술 스택
| 항목 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | React | 19.x |
| 빌드 도구 | Vite | 6.x |
| 라우팅 | React Router DOM | 7.x |
| 스타일링 | Tailwind CSS | 3.4 |
| 차트 | Plotly.js + Chart.js | 3.x / 4.x |
| 애니메이션 | Framer Motion | 12.x |
| 마크다운 | React Markdown + rehype-raw | 10.x |
| 프로덕션 서버 | Nginx (SPA + 리버스 프록시) | — |
| PWA | vite-plugin-pwa | 1.x |

## 디렉토리 구조

```
frontend/src/
├── api/                  # API 호출 레이어
│   ├── client.js         # fetchJson / postJson (base URL, auth 헤더 자동 처리)
│   ├── auth.js           # 인증 API (로그인, 회원가입, 토큰 갱신)
│   ├── narrative.js      # 키워드·케이스·내러티브 API
│   └── portfolio.js      # 포트폴리오·모의투자 API
├── components/
│   ├── common/           # 범용 재사용 (PenguinLoading, ErrorBoundary, UpdatePrompt 등)
│   ├── domain/           # 비즈니스 로직 (TermBottomSheet 등)
│   ├── layout/           # 레이아웃 (AppHeader, BottomNav, ChatFAB)
│   ├── charts/           # Plotly 기반 차트 컴포넌트
│   ├── tutor/            # AI 튜터 채팅 UI (TutorModal 등)
│   └── trading/          # 모의투자 UI
├── contexts/
│   ├── ThemeContext.jsx   # 다크모드 + CSS 변수 테마
│   ├── UserContext.jsx    # JWT 인증 상태
│   ├── PortfolioContext.jsx # 포트폴리오 데이터
│   ├── TutorContext.jsx   # 튜터 모달 상태 + 세션
│   └── TermContext.jsx    # 용어 하이라이트 상태
├── hooks/                # 커스텀 훅
├── pages/                # 페이지 컴포넌트 (각각 default export, lazy-loaded)
│   ├── Home.jsx          # 메인 — 오늘의 키워드 카드
│   ├── Auth.jsx          # 로그인 / 회원가입
│   ├── Onboarding.jsx    # 온보딩 플로우
│   ├── Search.jsx        # 검색
│   ├── Comparison.jsx    # 과거-현재 비교
│   ├── Story.jsx         # 스토리 뷰
│   ├── Companies.jsx     # 기업 목록
│   ├── History.jsx       # 히스토리
│   ├── Matching.jsx      # 케이스 매칭 (/case/:caseId)
│   ├── Narrative.jsx     # 내러티브 상세 (/narrative/:caseId)
│   ├── Portfolio.jsx     # 포트폴리오 + 모의투자
│   ├── Notifications.jsx # 알림
│   ├── Profile.jsx       # 프로필 / 설정
│   └── TutorChat.jsx     # 튜터 전체 화면 (/tutor)
├── providers/            # 추가 프로바이더
├── styles/               # 글로벌 스타일
├── utils/                # 유틸리티 함수
├── config.js             # 환경별 설정
├── App.jsx               # 루트 컴포넌트
└── main.jsx              # 엔트리 포인트
```

## Context Provider 계층

App.jsx에서 다음 순서로 래핑한다. 순서 변경 시 의존성 에러가 발생할 수 있으므로 주의.

```
BrowserRouter
  └─ ThemeProvider          (다크모드/라이트모드)
       └─ UserProvider       (JWT 인증, 사용자 정보)
            └─ PortfolioProvider  (포트폴리오 데이터)
                 └─ TutorProvider     (튜터 모달 on/off, 세션)
                      └─ TermProvider      (용어 하이라이트 상태)
                           └─ ErrorBoundary    (에러 폴백 UI)
                                └─ ToastProvider    (토스트 알림)
                                     └─ AppRoutes + 글로벌 컴포넌트
```

글로벌 컴포넌트(페이지 밖에서 항상 렌더링):
- `UpdatePrompt` — PWA 업데이트 프롬프트
- `TermBottomSheet` — 용어 바텀시트
- `TutorModal` — 튜터 모달
- `ChatFAB` — 튜터 호출 FAB 버튼
- `BottomNav` — 하단 네비게이션

## 라우팅

모든 페이지는 `React.lazy`로 코드 스플리팅된다. 인증이 필요한 페이지는 `ProtectedRoute`로 감싸고, 미인증 시 `/auth`로 리다이렉트한다.

| 경로 | 페이지 | 인증 |
|------|--------|------|
| `/onboarding` | Onboarding | 불필요 |
| `/auth` | Auth | 불필요 |
| `/` | Home | 필요 |
| `/search` | Search | 필요 |
| `/comparison` | Comparison | 필요 |
| `/story` | Story | 필요 |
| `/companies` | Companies | 필요 |
| `/history` | History | 필요 |
| `/case/:caseId` | Matching | 필요 |
| `/narrative/:caseId` | Narrative | 필요 |
| `/notifications` | Notifications | 필요 |
| `/portfolio` | Portfolio | 필요 |
| `/profile` | Profile | 필요 |
| `/tutor` | TutorChat | 필요 |

## API 레이어

### 구조
- `client.js`: 공통 HTTP 클라이언트 (`fetchJson`, `postJson`)
  - 프로덕션에서 base URL = 빈 문자열 (nginx 프록시로 `/api/v1/*` → `backend-api:8082`)
  - 로컬 개발 시 `VITE_FASTAPI_URL` 환경변수로 백엔드 주소 지정
  - `Authorization: Bearer <token>` 헤더를 자동으로 포함
- 도메인별 파일: `auth.js`, `narrative.js`, `portfolio.js` 등

### 주요 API 엔드포인트
| 프론트 함수 | 엔드포인트 | 설명 |
|-------------|-----------|------|
| `fetchTodayKeywords` | `GET /api/v1/keywords/today` | 오늘의 키워드 카드 |
| `fetchCase` | `GET /api/v1/cases/{id}` | 케이스 상세 (내러티브) |
| `sendTutorMessage` | `POST /api/v1/tutor/chat` | 튜터 대화 (SSE 스트리밍) |

## Nginx 리버스 프록시

프로덕션에서 `frontend/nginx.conf`가 Nginx 설정으로 사용된다.

| 경로 | 동작 |
|------|------|
| `/` | SPA — `try_files $uri $uri/ /index.html` |
| `/api/v1/*` | `proxy_pass http://backend-api:8082` (SSE 지원: `proxy_buffering off`) |
| `/api/auth/*` | rewrite → `/api/v1/auth/*` (레거시 호환) |
| `/api/health` | 헬스체크 프록시 |
| `*.js, *.css, *.png ...` | 정적 자산 — 7일 캐시 (`Cache-Control: public, immutable`) |
| `/sw.js`, `/manifest.webmanifest` | PWA 파일 — 캐시 방지 |

## 스타일링

- **Tailwind CSS** — `tailwind.config.js`에 커스텀 색상/테마 정의
- **CSS 변수 기반 테마**: `--color-background`, `--color-text` 등
- **다크모드**: `class` 전략 (ThemeContext에서 `<html>` 태그에 `dark` 클래스 토글)
- **주 색상**: `#FF6B00` (오렌지)
- **모바일 퍼스트**: max-width 480px 기준 디자인, 그 이상은 센터 정렬
