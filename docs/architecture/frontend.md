# 프론트엔드 아키텍처

## 기술 스택

- **React 19** + **Vite** (빌드 도구)
- **Tailwind CSS** (CSS variable 기반 테마, 다크모드 `class` 전략)
- **Nginx** (SPA 서빙 + 리버스 프록시)
- Primary color: `#FF6B00` (orange)
- Mobile-first: max-width 480px

## 디렉토리 구조

```
frontend/src/
├── api/            # 도메인별 API 호출 (fetchJson/postJson from client.js)
├── components/
│   ├── common/     # 재사용 컴포넌트
│   ├── domain/     # 비즈니스 로직 컴포넌트
│   ├── layout/     # AppHeader, BottomNav, ChatFAB
│   ├── charts/     # Plotly 시각화
│   ├── tutor/      # 챗봇 UI
│   └── trading/    # 모의투자
├── contexts/       # ThemeProvider, UserProvider, PortfolioProvider, TutorProvider, TermProvider
├── pages/          # 페이지 (default export, React.lazy 코드 스플리팅)
└── App.jsx         # 라우터 + Context Provider 래핑
```

## 라우팅

- React Router + `React.lazy` 코드 스플리팅
- Nginx에서 `/api/v1/*` 경로를 `backend-api:8082`로 프록시
- 레거시 `/api/auth/*`는 `/api/v1/auth/*`로 rewrite

## Context Provider 순서

```
ThemeProvider > UserProvider > PortfolioProvider > TutorProvider > TermProvider > ErrorBoundary > ToastProvider
```

## API 레이어

- `src/api/client.js`: `fetchJson`, `postJson` 헬퍼 (Authorization 헤더 자동 포함)
- Base URL: 프로덕션은 빈 문자열 (nginx 프록시), 로컬 개발은 `VITE_FASTAPI_URL`
- 도메인별 파일 분리 (keywords, cases, auth, portfolio 등)
