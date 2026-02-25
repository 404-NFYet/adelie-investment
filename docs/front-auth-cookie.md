# 프론트 작업 정리 (RefreshToken HttpOnly 쿠키 전환 기준)

## 현재 상태 요약
- **AccessToken/RefreshToken 모두 HttpOnly 쿠키로 전환**하는 흐름입니다.
- 프론트에서는 토큰을 직접 읽지 않고 **쿠키 기반 인증**으로 동작해야 합니다.

## 프론트에서 해야 할 작업

### 1) accessToken/refreshToken 저장/삭제 로직 제거
- `localStorage` 또는 기타 저장소에 access/refresh 토큰을 저장하지 않습니다.
- access/refresh 토큰 관련 `get/set/remove` 코드 제거 필요.

영향 위치 예시:
- `frontend/src/contexts/UserContext.jsx`
- `frontend/src/api/client.js`

### 2) refresh 요청을 쿠키 기반으로 변경
- `/api/v1/auth/refresh` 호출 시 refreshToken을 **body에 넣지 않음**
- 대신 쿠키가 자동 전송되도록 `credentials: 'include'` 설정

영향 위치 예시:
- `frontend/src/api/client.js`

### 3) 모든 인증 요청에 credentials 포함
- 쿠키 기반 인증을 사용하는 요청은 반드시 `credentials: 'include'` 필요
- 특히 refresh, 로그인/회원가입 후 인증된 요청 전체에 적용

영향 위치 예시:
- 공통 fetch 래퍼 또는 API 클라이언트

### 4) Authorization 헤더 의존 로직 제거
- AccessToken을 JS에서 읽을 수 없으므로 Authorization 헤더 전략을 제거합니다.
- 모든 인증은 쿠키 기반으로 전환됩니다.

### 5) CSRF 토큰 헤더 추가 (Double Submit Cookie)
- 로그인/회원가입/리프레시 시 내려오는 **CSRF 쿠키** 값을 읽어
  모든 `POST/PUT/PATCH/DELETE` 요청에 `X-CSRF-Token` 헤더로 전송해야 합니다.
- `/api/v1/auth/csrf`로 CSRF 토큰만 발급받을 수도 있습니다.

## 추가 고려사항
- 인증 상태 판단은 `/api/v1/auth/me` 호출 결과로 결정하도록 단순화하는 편이 안전합니다.
- 페이지 초기 로딩 시 `/api/v1/auth/refresh`를 호출하여 쿠키 갱신 여부를 확인할 수 있습니다.

## 체크리스트
- [ ] access/refresh 로컬 저장 제거
- [ ] refresh 요청은 쿠키 기반으로 변경
- [ ] 모든 인증 요청에 `credentials: 'include'`
- [ ] Authorization 헤더 의존 로직 제거
- [ ] 모든 state-changing 요청에 `X-CSRF-Token` 헤더 추가
