# 모바일 기기 기준표

Playwright E2E 테스트 대상 기기 목록. `playwright.config.js`의 `projects` 배열과 일치.

## 지원 기기 (9종)

| Project 이름 | 브랜드 | viewport (w×h) | DPR | 비고 |
|-------------|--------|----------------|-----|------|
| iPhone SE 3rd | Apple | 375×667 | 2 | 최소 iOS 지원 기기 |
| iPhone 16 | Apple | 393×852 | 3 | |
| iPhone 16 Plus | Apple | 430×932 | 3 | |
| iPhone 16 Pro | Apple | 402×874 | 3 | |
| iPhone 16 Pro Max | Apple | 440×956 | 3 | 최대 iOS viewport |
| Galaxy S24 | Samsung | 360×780 | 3 | |
| Galaxy S25 | Samsung | 360×780 | 3 | S24와 동일 viewport |
| Galaxy S25 Plus | Samsung | 412×891 | 3 | |
| Galaxy S25 Ultra | Samsung | 412×891 | 3.5 | |

## 설계 기준

- **최소 viewport**: 360px (Galaxy S24/S25)
- **최대 viewport**: 440px (iPhone 16 Pro Max)
- **서비스 max-width**: 480px (`max-w-mobile`)
- **터치 영역 최소**: 40px × 40px (iOS HIG: 44px 권장)

## 반응형 설계 원칙

| 범주 | 패턴 | 비고 |
|------|------|------|
| 컨테이너 | `max-w-mobile` (480px) | |
| 타이포그래피 | `clamp(최솟값, 선호값vw, 최댓값)` | |
| 여백 | `px-4`~`px-5` | 총 수평 패딩 ≤ 64px |
| 이미지 | `max-w-[80vw] h-auto` | 360px에서 잘림 방지 |
| 터치 영역 | `h-10 w-10` 이상 | |
| 브레이크포인트 | `sm:` 클래스 사용 금지 | 640px > 480px 서비스 max |

## 테스트 파일 목록

| 파일 | Test IDs | 설명 |
|------|----------|------|
| `e2e/landing-mobile.spec.js` | FE-LAND-M01~05 | 랜딩 페이지 반응형 |
| `e2e/daily-quiz-modal-mobile.spec.js` | FE-QUIZ-M01~03 | 퀴즈 모달 반응형 |
| `e2e/agent-canvas-mobile.spec.js` | FE-AGENT-M01~04 | Agent Canvas 반응형 |

## 실행 방법

```bash
# 특정 기기로 테스트
cd frontend
npx playwright test --project="Galaxy S25" --project="iPhone SE 3rd"

# 모바일 랜딩 테스트만
npx playwright test e2e/landing-mobile.spec.js

# 전체 모바일 테스트
npx playwright test e2e/landing-mobile.spec.js e2e/daily-quiz-modal-mobile.spec.js e2e/agent-canvas-mobile.spec.js

# 모든 E2E
make test-e2e
```
