# 프론트엔드 로컬 개발 가이드

> Frontend 팀원(손영진) 및 UI 관련 작업을 하는 모든 팀원을 위한 로컬 개발 환경 설정 가이드.

## 사전 준비

- Node.js 18+ 및 npm 설치
- 루트 `.env` 파일 준비 (`.env.example`에서 복사)

---

## 방법 1: deploy-test API 사용 (가장 간단)

Backend를 로컬에서 실행하지 않고 deploy-test 서버(`10.10.10.20`)의 API를 직접 사용한다. Backend/DB 설정이 필요 없어 **프론트엔드만 작업할 때 권장**한다.

### 설정

루트 `.env` 파일에서 `VITE_FASTAPI_URL`을 설정한다:

```env
VITE_FASTAPI_URL=http://10.10.10.20:8082
```

### 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3001`로 접속한다.

### 동작 원리

- `VITE_FASTAPI_URL`이 설정되면 `frontend/src/config.js`의 `API_BASE_URL`이 해당 URL로 설정된다
- 모든 API 호출(`fetchJson`, `postJson`)이 `http://10.10.10.20:8082/api/v1/*`로 직접 요청된다
- Vite 개발 서버의 proxy 설정은 무시된다

### 주의사항

- deploy-test 서버가 실행 중이어야 한다
- CORS 이슈가 발생할 수 있다 (Backend에 `http://localhost:3001`이 CORS 허용 목록에 있어야 함)
- deploy-test DB의 데이터를 사용하므로 로컬과 데이터가 다를 수 있다

---

## 방법 2: 로컬 Backend + Frontend

Backend와 Frontend를 모두 로컬에서 실행한다. **Backend API를 함께 개발/디버깅할 때 권장**한다.

### 사전 준비

- Python 3.12 가상환경: `.venv/bin/python`
- PostgreSQL 접속 가능 (shared 또는 로컬 Docker)
- 루트 `.env`에 올바른 `DATABASE_URL` 설정

### 설정

루트 `.env`에서 `VITE_FASTAPI_URL`을 비운다 (또는 삭제):

```env
VITE_FASTAPI_URL=
```

### 실행 (터미널 2개 필요)

**터미널 1 - Backend:**

```bash
cd fastapi
../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```

또는 프로젝트 루트에서:

```bash
make dev-api-local
```

**터미널 2 - Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### 동작 원리

- `VITE_FASTAPI_URL`이 빈 문자열이면 `API_BASE_URL`도 빈 문자열이 된다
- API 호출이 `/api/v1/*` (상대 경로)로 요청된다
- Vite 개발 서버의 proxy가 `/api/v1/*` 요청을 `http://localhost:8082`로 전달한다

`vite.config.js`의 proxy 설정:

```js
proxy: {
  '/api/v1': {
    target: 'http://localhost:8082',
    changeOrigin: true,
  },
  '/api/auth': {
    target: 'http://localhost:8082',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/auth/, '/api/v1/auth'),
  },
}
```

### 장점

- Backend 코드를 직접 수정하며 디버깅 가능 (--reload로 핫 리로드)
- Swagger UI(`http://localhost:8082/docs`)로 API 직접 테스트 가능
- CORS 이슈 없음 (Vite proxy가 처리)

---

## 방법 3: Docker Backend + 로컬 Frontend

Backend를 Docker로, Frontend는 로컬에서 실행한다. **Backend 코드를 수정하지 않으면서 전체 스택이 필요할 때 권장**한다.

### 실행

**터미널 1 - Docker Backend:**

```bash
make dev-api
```

이 명령은 `docker-compose.dev.yml`에서 `postgres` + `redis` + `backend-api`를 실행한다. Backend가 `localhost:8082`에서 서비스된다.

**터미널 2 - 로컬 Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### 설정

루트 `.env`에서 `VITE_FASTAPI_URL`을 비운다:

```env
VITE_FASTAPI_URL=
```

### 동작 원리

방법 2와 동일하게 Vite proxy가 `localhost:8082`(Docker Backend)로 요청을 전달한다.

### 장점

- DB, Redis가 Docker로 자동 관리 (별도 설치 불요)
- Backend 핫 리로드 지원 (Docker volume mount)
- `chatbot/`, `datapipeline/` 모듈도 Docker에 마운트되어 함께 동작

---

## 프론트엔드 디렉토리 구조

```
frontend/src/
├── App.jsx                    # 메인 앱 (Router, Context Providers)
├── config.js                  # API_BASE_URL 설정
├── main.jsx                   # React 진입점
│
├── pages/                     # 페이지 (React.lazy로 코드 스플리팅)
│   ├── Home.jsx               # 메인 - 오늘의 키워드
│   ├── Auth.jsx               # 로그인/회원가입
│   ├── Onboarding.jsx         # 온보딩
│   ├── Search.jsx             # 검색
│   ├── Story.jsx              # 사례 스토리
│   ├── Comparison.jsx         # 과거-현재 비교
│   ├── Companies.jsx          # 관련 기업
│   ├── Matching.jsx           # 케이스 매칭
│   ├── Narrative.jsx          # 내러티브 (6페이지 브리핑)
│   ├── History.jsx            # 키워드 히스토리
│   ├── Notifications.jsx      # 알림
│   ├── Portfolio.jsx          # 포트폴리오 (모의투자)
│   ├── Profile.jsx            # 프로필
│   ├── TutorChat.jsx          # AI 튜터 채팅 (전체 페이지)
│   └── index.js               # 일괄 export
│
├── components/
│   ├── common/                # 범용 재사용 컴포넌트
│   │   ├── ErrorBoundary.jsx  # 에러 바운더리
│   │   ├── PenguinLoading.jsx # 로딩 스피너 (펭귄)
│   │   ├── PenguinMascot.jsx  # 마스코트 SVG
│   │   ├── PenguinSVG.jsx     # 펭귄 SVG
│   │   ├── Toast.jsx          # 토스트 알림
│   │   ├── SplashScreen.jsx   # 스플래시 화면
│   │   ├── AuthPrompt.jsx     # 인증 프롬프트
│   │   ├── InstallPrompt.jsx  # PWA 설치 프롬프트
│   │   ├── UpdatePrompt.jsx   # 업데이트 프롬프트
│   │   └── FeedbackWidget.jsx # 피드백 위젯
│   │
│   ├── domain/                # 비즈니스 로직 컴포넌트
│   │   ├── KeywordCard.jsx    # 키워드 카드
│   │   ├── CompanyCard.jsx    # 기업 카드
│   │   ├── HighlightedText.jsx # 용어 하이라이트 텍스트
│   │   ├── TermBottomSheet.jsx # 용어 바텀시트
│   │   ├── ThinkingPoint.jsx  # 생각해볼 점
│   │   ├── OpinionPoll.jsx    # 의견 투표
│   │   ├── NextStepButton.jsx # 다음 단계 버튼
│   │   └── TradeModal.jsx     # 매매 모달
│   │
│   ├── layout/                # 레이아웃 컴포넌트
│   │   ├── AppHeader.jsx      # 상단 헤더
│   │   ├── BottomNav.jsx      # 하단 네비게이션
│   │   └── ChatFAB.jsx        # 튜터 채팅 FAB 버튼
│   │
│   ├── charts/                # 차트 (Plotly 기반)
│   │   ├── PlotlyChart.jsx    # Plotly 래퍼
│   │   ├── ChartContainer.jsx # 차트 컨테이너
│   │   ├── TrendLineChart.jsx # 추세 선 그래프
│   │   ├── ComparisonBarChart.jsx # 비교 막대 그래프
│   │   ├── ComparisonMatrix.jsx   # 비교 매트릭스
│   │   ├── SingleBarChart.jsx # 단일 막대 그래프
│   │   ├── SimilarityChart.jsx # 유사도 차트
│   │   ├── TopMoversChart.jsx # 등락률 차트
│   │   ├── MarketIndexCard.jsx # 시장 지수 카드
│   │   ├── MetricGauge.jsx    # 지표 게이지
│   │   ├── RiskIndicatorChart.jsx # 리스크 지표
│   │   ├── StepPlaceholder.jsx # 스텝 플레이스홀더
│   │   └── index.js / index.jsx
│   │
│   ├── tutor/                 # AI 튜터 채팅 UI
│   │   ├── TutorModal.jsx     # 튜터 모달 (글로벌)
│   │   ├── TutorPanel.jsx     # 튜터 패널
│   │   ├── MessageBubble.jsx  # 메시지 버블
│   │   ├── ChatInput.jsx      # 채팅 입력
│   │   └── SessionSidebar.jsx # 세션 사이드바
│   │
│   ├── trading/               # 모의투자
│   │   ├── StockDetail.jsx    # 종목 상세
│   │   ├── StockSearch.jsx    # 종목 검색
│   │   ├── MiniChart.jsx      # 미니 차트
│   │   ├── RewardCard.jsx     # 보상 카드
│   │   └── Leaderboard.jsx    # 리더보드
│   │
│   └── index.js               # 일괄 export
│
├── api/                       # API 호출 (도메인별 분리)
│   ├── client.js              # fetchJson / postJson / deleteJson (공통 HTTP 클라이언트)
│   ├── index.js               # casesApi, keywordsApi, notificationApi + re-export
│   ├── auth.js                # authApi (로그인, 회원가입, 토큰)
│   ├── narrative.js           # narrativeApi (내러티브, 브리핑)
│   └── portfolio.js           # portfolioApi (포트폴리오, 매매)
│
├── contexts/                  # React Context Providers
│   ├── ThemeContext.jsx       # 다크/라이트 테마
│   ├── UserContext.jsx        # 사용자 인증 상태
│   ├── PortfolioContext.jsx   # 포트폴리오 데이터
│   ├── TutorContext.jsx       # 튜터 모달 상태
│   ├── TermContext.jsx        # 용어 바텀시트 상태
│   └── index.js               # 일괄 export
│
├── hooks/                     # 커스텀 훅
│   ├── useFetch.js            # 데이터 fetching 훅
│   ├── useCountUp.js          # 숫자 카운트업 애니메이션
│   ├── useDwellReward.js      # 체류 보상 훅
│   └── useOnlineStatus.js     # 온라인/오프라인 감지
│
└── styles/
    └── globals.css            # 글로벌 CSS (Tailwind base + 커스텀 변수)
```

### Context Provider 래핑 순서

`App.jsx`에서 Provider를 다음 순서로 래핑한다:

```
BrowserRouter
  └── ThemeProvider
       └── UserProvider
            └── PortfolioProvider
                 └── TutorProvider
                      └── TermProvider
                           └── ErrorBoundary
                                └── ToastProvider
                                     └── AppRoutes + TermBottomSheet + TutorModal + ChatFAB + BottomNav
```

### 페이지 라우팅

| 경로 | 페이지 | 인증 필요 |
|------|--------|----------|
| `/onboarding` | Onboarding | 불요 |
| `/auth` | Auth | 불요 |
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

---

## LXD 컨테이너에서 포트 접근

팀원별 LXD 개발 컨테이너 내부에서 작업하는 경우, 호스트에서 컨테이너의 포트에 접근하기 위해 SSH 포트 포워딩이 필요하다.

### 방법 1: SSH 포트 포워딩 (로컬 브라우저 사용)

개인 PC의 브라우저에서 LXD 컨테이너의 서비스에 접속하려면:

```bash
# Frontend(:3001) + Backend(:8082) 동시 포워딩
ssh -L 3001:localhost:3001 -L 8082:localhost:8082 dev-{name}
```

이후 로컬 PC 브라우저에서 `http://localhost:3001`으로 접속한다.

### 방법 2: LXD 컨테이너 IP로 직접 접속

infra-server(`10.10.10.10`)와 같은 네트워크에 있다면, LXD 컨테이너의 IP로 직접 접속 가능하다:

```bash
# LXD 컨테이너 IP 확인 (infra-server에서)
lxc list

# 예: dev-youngjin 컨테이너 IP가 10.10.10.101인 경우
# 브라우저에서 http://10.10.10.101:3001 접속
```

### 방법 3: Vite host 설정 (이미 적용됨)

`vite.config.js`에 `host: '0.0.0.0'`이 설정되어 있어, LXD 컨테이너 내부에서 실행해도 외부에서 접근 가능하다:

```js
server: {
  host: '0.0.0.0',   // 모든 인터페이스에서 수신
  port: 3001,
  strictPort: true,
}
```

---

## 자주 발생하는 문제

### CORS 에러 (방법 1 사용 시)

deploy-test API를 직접 호출할 때 CORS 에러가 발생하면:

- Backend의 `CORS_ALLOWED_ORIGINS`에 `http://localhost:3001`이 포함되어 있는지 확인
- deploy-test 서버의 `.env`에서 `CORS_ALLOWED_ORIGINS` 업데이트 필요 시 도형준에게 요청

### `npm run dev` 실행 시 포트 충돌

`strictPort: true` 설정으로 3001 포트가 이미 사용 중이면 에러가 발생한다:

```bash
# 사용 중인 프로세스 확인
lsof -i :3001

# 프로세스 종료 후 재실행
kill -9 <PID>
npm run dev
```

### API 요청이 404 반환

- `VITE_FASTAPI_URL` 설정 확인: 빈 문자열이면 proxy, 값이 있으면 직접 호출
- Backend가 실행 중인지 확인: `curl http://localhost:8082/api/v1/health`
- Vite를 재시작해야 `.env` 변경이 반영됨 (`npm run dev` 재실행)

### `node_modules` 관련 에러

```bash
# node_modules 삭제 후 재설치
rm -rf frontend/node_modules frontend/package-lock.json
cd frontend && npm install
```
