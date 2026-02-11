---
paths:
  - "frontend/**/*.{js,jsx}"
---

# Frontend 코드 컨벤션

## API 호출
- `src/api/client.js`의 `fetchJson`/`postJson` 사용
- 도메인별 파일 분리: `src/api/{domain}.js`
- 프로덕션에서 base URL은 빈 문자열 (nginx 프록시)

## 컴포넌트 구조
- `common/` — 재사용 가능한 범용 컴포넌트
- `domain/` — 비즈니스 로직 컴포넌트
- `layout/` — AppHeader, BottomNav, ChatFAB
- `charts/` — Plotly 기반 차트
- `tutor/` — 채팅 UI
- `trading/` — 모의투자

## 페이지
- `pages/` 디렉토리에 각 페이지 default export
- `App.jsx`에서 `React.lazy`로 코드 스플리팅
- `pages/index.js`에서 일괄 export

## Context
- `contexts/index.js`에서 일괄 export
- Provider 래핑 순서: Theme > User > Portfolio > Tutor > Term > ErrorBoundary > Toast

## 스타일링
- Tailwind CSS + CSS 변수 기반 테마
- 다크모드: `class` 전략
- 주 색상: `#FF6B00` (orange)
- 모바일 퍼스트: max-width 480px

## 기타
- 한글 UI, 한글 주석
- 더미/목 데이터 사용 금지 — 실 API 연동만
