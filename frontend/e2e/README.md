# E2E 테스트 가이드 (Playwright)

## 실행 방법

```bash
# 전체 실행 (CI 기준)
make test-e2e

# 특정 테스트 ID만 실행
npx playwright test --grep "FE-PORT" --reporter=list
npx playwright test --grep "FE-PROF" --reporter=list
npx playwright test --grep "FE-VIZ"  --reporter=list

# HTML 리포트 생성
npx playwright test --reporter=html
npx playwright show-report

# 특정 파일만 실행
npx playwright test e2e/smoke.spec.js
npx playwright test e2e/portfolio-trading.spec.js
```

> **선행 조건**: `make dev-api`(백엔드) + `npm run dev`(프론트)가 모두 기동 중이어야 합니다.

---

## 테스트 ID 매핑 테이블

| ID 범위 | 파일 | 라우트 | 디바이스 |
|---------|------|--------|---------|
| FE-SMOKE-01~06 | `smoke.spec.js` | 여러 | Desktop |
| FE-LAND-M01~05 | `landing-mobile.spec.js` | `/` | 9종 모바일 |
| FE-ONB-01~06 | `mobile-full-flow.spec.js` | `/onboarding` | Mobile (390px) |
| FE-AUTH-01~05 | `auth-flow.spec.js` | `/auth` | Desktop |
| FE-SEARCH-01~04 | `search-flow.spec.js` | `/search` | Desktop |
| FE-MATCH-01~08 | `comprehensive-fix-test.spec.js` | `/comparison` | Desktop |
| FE-STORY-01~06 | `comprehensive-fix-test.spec.js` | `/story` | Desktop |
| FE-COMP-01~08 | `comprehensive-fix-test.spec.js` | `/comparison` | Desktop |
| FE-COMPANIES-01~04 | `comprehensive-fix-test.spec.js` | `/companies` | Desktop |
| FE-NARR-01~03 | `narrative-flow.spec.js` | `/narrative/:id` | Desktop |
| FE-TUTOR-01~03 | `tutor-chat.spec.js` | `/agent` | Desktop |
| FE-AGENT-M01~04 | `agent-canvas-mobile.spec.js` | `/agent` | 9종 모바일 |
| FE-QUIZ-M01~03 | `daily-quiz-modal-mobile.spec.js` | `/home` | 9종 모바일 |
| FE-VIZ-01~03 | `tutor-visualization.spec.js` | `/agent` | Desktop |
| FE-PORT-01~05, M01 | `portfolio-trading.spec.js` | `/portfolio` | Desktop + Mobile(360px) |
| FE-PROF-01~04, M01 | `profile-settings.spec.js` | `/profile` | Desktop + Mobile(390px) |
| FE-NOT-01~03 | `notifications.spec.js` | `/notifications` | Desktop |
| FE-EDU-01~03, M01 | `education-flow.spec.js` | `/education` | Desktop + Mobile(390px) |
| FE-CASE-01~02 | `case-redirect.spec.js` | `/case/:id` | Desktop |
| REG-PRE, TEST1~3 | `regression.spec.js` | `/story`, `/comparison`, `/companies` | Mobile (390px) |

---

## 타임아웃 표준

모든 스펙 파일은 아래 상수를 사용합니다:

```js
const TIMEOUT = {
  fast: 5_000,     // 즉각 DOM 변경 (버튼 클릭 후 상태 변화 등)
  network: 10_000, // API 응답 대기
  llm: 20_000,     // LLM 스트리밍 응답 (튜터 채팅 등)
};
```

---

## 선택자 우선순위

Playwright 권장 순서를 따릅니다:

1. `getByRole()` — ARIA 역할 기반 **(최우선)**
2. `getByTestId()` — `data-testid` 속성
3. `getByText()` / `getByPlaceholder()` — 텍스트/플레이스홀더
4. CSS 선택자 — 최후 수단 (리팩터링에 취약)

### data-testid 작성 규칙 (신규 컴포넌트 필수)

```jsx
// ✅ 권장: 컴포넌트에 data-testid 부여
<button data-testid="narrative-next-btn" onClick={handleNext}>
  다음
</button>

// ✅ 테스트에서 사용
await page.getByTestId('narrative-next-btn').click();
```

- 형식: `{도메인}-{컴포넌트}-{역할}` (kebab-case, 소문자)
- 예: `portfolio-buy-btn`, `profile-logout-btn`, `narrative-next-btn`
- **신규 컴포넌트 PR에는 E2E 대상 인터랙티브 요소에 반드시 추가**

---

## 인증이 필요한 테스트

`portfolio-trading.spec.js`, `profile-settings.spec.js`, `notifications.spec.js`는 로그인이 필요합니다.
각 파일의 `loginAnd*` 헬퍼가 타임스탬프 기반 임시 계정을 생성합니다.

```js
// 예시 패턴
async function loginAndGoToPortfolio(page) {
  const ts = Date.now();
  await page.goto('/auth');
  // 회원가입 → 홈 이동 → 목표 라우트 이동
  ...
}
```

---

## 자주 발생하는 실패 원인

| 증상 | 원인 | 해결 |
|------|------|------|
| `Timeout: page.goto('/auth')` | 백엔드 미기동 | `make dev-api` 실행 후 재시도 |
| `test.skip` 다수 | 서버 데이터 없음 | `make seed` 또는 파이프라인 실행 |
| `FE-VIZ` 실패 | LLM 응답 없음 | `.env`의 `OPENAI_API_KEY` 확인 |
| `FE-PORT` 매수 버튼 미노출 | 보유 종목 없음 | 정상 동작 — skip으로 처리됨 |
