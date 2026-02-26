# 공용 계정 관리

## 공용 Google 계정

팀 공용 서비스 관리에 사용하는 Google 계정.

| 항목 | 값 |
|------|------|
| 이메일 | (팀장에게 문의) |
| 용도 | Clarity, LangSmith SSO, 기타 외부 서비스 |
| 관리 담당자 | 도형준 (인프라) |

## 서비스별 접속 정보

| 서비스 | URL | 로그인 방식 | 용도 |
|--------|-----|------------|------|
| Clarity | [clarity.microsoft.com](https://clarity.microsoft.com) | Google SSO | 세션 리플레이, 히트맵 |
| PostHog | [analytics.adelie-invest.com](https://analytics.adelie-invest.com) | 자체 계정 | 퍼널 분석, 이벤트, Feature Flag |
| LangSmith | [smith.langchain.com](https://smith.langchain.com) | Google SSO / API Key | LLM 모니터링, 트레이싱 |
| Grafana | [monitoring.adelie-invest.com](https://monitoring.adelie-invest.com) | 자체 계정 | 인프라 모니터링 |
| Streamlit 대시보드 | [dashboard.adelie-invest.com](https://dashboard.adelie-invest.com) | 인증 없음 | 데이터 대시보드 |
| Docker Hub | [hub.docker.com](https://hub.docker.com) | 개인 계정 | Docker 이미지 푸시 (dorae222/* 네임스페이스) |

## API Key 관리 규칙

1. **저장 위치**: `.env` 파일에만 저장 — git 커밋 절대 금지
2. **공유 방법**: Discord DM 또는 비공개 채널
3. **로테이션**: 유출 시 즉시 교체, 정기 교체 불필요 (데모 기간)
4. **신규 팀원**: 팀장/인프라 담당자에게 `.env` 파일 요청

## 계정 인수인계 절차

1. 모든 서비스의 관리자 권한을 신규 담당자에게 부여
2. 비밀번호 변경 (해당되는 경우)
3. API Key 로테이션 (해당되는 경우)
4. Discord #infra 채널에 인수인계 완료 공지
5. 이 문서 업데이트 (관리 담당자 변경)
