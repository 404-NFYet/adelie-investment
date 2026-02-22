# 프론트엔드 개발 가이드 — 손영진

## 환경 정보
- LXD 컨테이너: `ssh dev-yj99son`
- Git 설정: user.name=YJ99Son, user.email=syjin2008@naver.com
- 브랜치: `dev/frontend`

## 개발 시작

### Docker 환경 (권장)
```bash
make dev-frontend
# 또는
docker compose -f docker-compose.dev.yml up frontend
```
- URL: http://localhost:3001
- Vite HMR 활성화 (코드 수정 시 자동 반영)
- nginx를 통해 `/api/v1/*` 요청은 backend-api:8082로 프록시

### 로컬 환경 (Docker 없이)
```bash
cd frontend
npm install
npm run dev
```
- `.env` 파일에서 `VITE_FASTAPI_URL=http://localhost:8082` 설정 필요
- Backend API가 로컬에서 실행 중이어야 함

## 담당 디렉토리

```
frontend/
├── src/
│   ├── pages/              # 라우트별 페이지 컴포넌트 (lazy load)
│   │   ├── KeywordPage.jsx
│   │   ├── CasePage.jsx
│   │   ├── TradingPage.jsx
│   │   └── ...
│   ├── components/         # 재사용 가능한 컴포넌트
│   │   ├── common/         # Button, Card, Modal 등
│   │   ├── domain/         # KeywordCard, CaseTimeline 등
│   │   ├── layout/         # AppHeader, BottomNav, ChatFAB
│   │   ├── charts/         # Plotly 차트 컴포넌트
│   │   ├── tutor/          # 튜터 채팅 UI
│   │   └── trading/        # 모의투자 UI
│   ├── contexts/           # React Context Providers
│   │   ├── UserContext.jsx
│   │   ├── PortfolioContext.jsx
│   │   ├── TutorContext.jsx
│   │   └── index.js        # 통합 export
│   ├── api/                # API 클라이언트 레이어
│   │   ├── client.js       # fetchJson, postJson 유틸
│   │   ├── auth.js
│   │   ├── keywords.js
│   │   ├── cases.js
│   │   ├── tutor.js
│   │   └── ...
│   ├── App.jsx             # 라우터 설정, Context Provider 체인
│   └── main.jsx            # 진입점
├── public/                 # 정적 파일
├── tailwind.config.js      # Tailwind CSS 설정
├── vite.config.js          # Vite 번들러 설정
└── nginx.conf              # 프로덕션 nginx 설정
```

### 핵심 파일
- `App.jsx`: React Router v6 설정, Context Provider 체인 (Theme > User > Portfolio > Tutor > Term > Error > Toast)
- `api/client.js`: Authorization 헤더 자동 포함, 에러 핸들링 통합
- `contexts/index.js`: 모든 Context export
- `tailwind.config.js`: CSS 변수 기반 테마 (dark mode: class 전략), primary 색상: #FF6B00

## 개발 워크플로우

1. **새 페이지 추가**
   ```bash
   # 1. pages/ 에 컴포넌트 생성
   touch src/pages/NewPage.jsx

   # 2. App.jsx에 lazy import + route 추가
   # const NewPage = React.lazy(() => import('./pages/NewPage'));
   # <Route path="/new" element={<NewPage />} />
   ```

2. **API 연동**
   ```javascript
   // src/api/new_feature.js
   import { fetchJson, postJson } from './client';

   export const getFeature = () => fetchJson('/api/v1/feature');
   export const createFeature = (data) => postJson('/api/v1/feature', data);
   ```

3. **스타일링**
   - Tailwind utility class 우선 사용
   - 다크모드: `dark:` prefix (예: `bg-white dark:bg-gray-800`)
   - 커스텀 색상은 `tailwind.config.js`의 `theme.extend.colors`에 추가

4. **컴포넌트 분리**
   - 3회 이상 반복되면 `components/common/` 또는 `components/domain/`으로 추출
   - Props drilling이 2단계 이상이면 Context 고려

## 테스트

### E2E 테스트 (Playwright)
```bash
make test-e2e
# 또는
cd frontend && npx playwright test

# 특정 ID 필터링
npx playwright test --grep "FE-SMOKE"
npx playwright test --grep "FE-PORT"

# HTML 리포트
npx playwright test --reporter=html && npx playwright show-report
```

- 테스트 파일: `frontend/e2e/*.spec.js` (18개 파일, ~90개 테스트)
- 상세 가이드: [`frontend/e2e/README.md`](../../frontend/e2e/README.md)
- 테스트 ID 체계: `FE-{도메인}-{번호}` (예: `FE-PORT-01`, `FE-NARR-03`)

#### 신규 컴포넌트 작성 시 E2E 필수 사항

인터랙티브 요소(버튼, 입력창, 모달 트리거)에 `data-testid` 추가:

```jsx
// ✅ 필수: 클릭/입력 대상 요소에 testid 부여
<button data-testid="profile-logout-btn" onClick={handleLogout}>
  로그아웃
</button>
<input data-testid="stock-search-input" placeholder="종목 검색" />
```

형식: `{도메인}-{역할}-{타입}` (kebab-case)
예: `portfolio-buy-btn`, `profile-difficulty-select`, `narrative-next-btn`

**PR 체크리스트에 추가**: 새 컴포넌트 PR → `frontend/e2e/` 테스트 업데이트 또는 신규 작성

### 브라우저 테스트
- Chrome DevTools → Responsive 모드 (480px width)
- 다크모드 토글 확인 (AppHeader 우측 상단)

## 다른 파트와의 연동

### Backend API (허진서)
- **영향받는 경우**: API 엔드포인트 변경, response 스키마 변경
- **대응**: `src/api/*.js` 파일 수정, TypeScript 타입 정의 있다면 업데이트
- **주의**: JWT 토큰 만료 시 401 처리 → `client.js`에서 자동 로그아웃

### Chatbot (정지훈)
- **영향받는 경우**: SSE 이벤트 타입 변경, 튜터 응답 포맷 변경
- **대응**: `TutorContext.jsx`, `components/tutor/ChatMessage.jsx` 수정
- **주의**: `event.data` 파싱 로직, 용어 하이라이트 렌더링

### Pipeline (안례진)
- **영향받는 경우**: narrative 구조 변경, glossary 포맷 변경
- **대응**: `pages/CasePage.jsx`, `components/domain/CaseTimeline.jsx` 수정
- **주의**: DB에 저장된 데이터 구조와 UI 렌더링 로직 일치 확인

### Infra (도형준)
- **영향받는 경우**: nginx 설정 변경, 환경변수 변경, Docker 이미지 재빌드
- **대응**: `.env.example` 업데이트, `docker-compose.dev.yml` 확인
- **주의**: 프로덕션 배포 전 `make build-frontend` 테스트

## 커밋 전 체크리스트
- [ ] `git config user.name` = YJ99Son
- [ ] `git config user.email` = syjin2008@naver.com
- [ ] ESLint 경고 해결
- [ ] 다크모드에서 정상 작동 확인
- [ ] 480px 모바일 뷰에서 레이아웃 깨짐 없음
- [ ] 커밋 메시지 형식: `feat: 키워드 카드 UI 개선` (한글, type prefix)
