# 프로젝트 변경이력 (Changes)

## 개요
Adelie Investment 프로젝트의 개발 과정을 파트별로 기록한 문서.
각 팀원의 기여를 STAR 형식으로 정리하여 프로젝트 진행 상황을 추적한다.

## 개발 타임라인

### Phase 1: 프로젝트 초기 구축 (2026-01-20 ~ 02-06)
- FastAPI + React 기본 구조 구축
- PostgreSQL/Redis/MinIO 인프라 셋업
- JWT 인증, 기본 API 엔드포인트 개발
- 데이터 파이프라인 초기 설계

### Phase 2: 핵심 기능 구현 (2026-02-06 ~ 02-12)
- LangGraph 18노드 파이프라인 구축
- AI 튜터 챗봇 기본 구조
- 프론트엔드 페이지 구현 (Home, Narrative, Portfolio, Search)
- 주식 시뮬레이션 거래 기능

### Phase 3: 통합 & 최적화 (2026-02-12 ~ 02-14)
- 데이터 파이프라인 → API → 프론트엔드 E2E 연동
- 모니터링 인프라 (Prometheus + Grafana)
- 문서 구조 개편

### Phase 4: 기능 고도화 (2026-02-14 ~ 02-17)
- Figma 기반 프론트엔드 통합
- CRITICAL/HIGH 이슈 수정 (보안, 성능, 안정성)
- CI/CD 파이프라인, LocalStack+Terraform
- 챗봇 복원, Google Gemini 지원

### Phase 5: 최종 안정화 + 모니터링 (2026-02-17 ~ 02-27)
- prod-final 브랜치 전환, Docker 태그 정책 변경 (`:latest` → `prod-YYYYMMDD`)
- Prometheus + Grafana 백엔드 메트릭 통합
- 챗봇 Chart-First 아키텍처 + Hybrid Clarification
- 파이프라인 내러티브 중복 제거 + 포맷팅 개선
- 프론트엔드 PostHog/Clarity 분석 이벤트 트래킹
- 문서 전면 업데이트 + v2.0 릴리스

## 파트별 기여 요약

| 파트 | 담당자 | 커밋 수 | 주요 기여 |
|------|--------|---------|-----------|
| 인프라 | 도형준 (dorae222) | ~379 | Docker, LXD, 모니터링, CI/CD, Terraform |
| 프론트엔드 | 손영진 (YJ99Son) | ~208 | UI/UX 전체, Figma 랜딩, ECharts, 내러티브 |
| 파이프라인 QA | 안례진 (ryejinn) | ~85 | 데이터 파이프라인, 프롬프트, 테스트 |
| 백엔드 | 허진서 (jjjh02) | ~58 | JWT 인증, DB 설계, API 최적화, 보안 강화 |
| AI/챗봇 | 정지훈 (J2hoon10) | ~52 | LangGraph 에이전트, 튜터, 프롬프트 엔지니어링 |

## 파일 목록

| 파일 | 담당자 | 역할 |
|------|--------|------|
| [YJ99Son.md](./YJ99Son.md) | 손영진 | 프론트엔드 |
| [J2hoon10.md](./J2hoon10.md) | 정지훈 | AI/챗봇 |
| [ryejinn.md](./ryejinn.md) | 안례진 | 파이프라인 QA |
| [jjjh02.md](./jjjh02.md) | 허진서 | 백엔드 |
| [dorae222.md](./dorae222.md) | 도형준 | 인프라 |
