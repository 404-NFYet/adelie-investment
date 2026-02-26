# Adelie Investment 문서

"History Repeats Itself" - AI 기반 금융 교육 플랫폼

> **필독**: [브랜치 전략 & 개발 워크플로우](getting-started/workflow.md) — 브랜치 구조, merge/pull 방향, PR 규칙, 배포 절차

## 시작하기 (Getting Started)

| 문서 | 설명 |
|------|------|
| [**브랜치 전략 & 워크플로우**](getting-started/workflow.md) | **브랜치 구조, merge/pull 방향, PR 규칙, 배포, 커밋 컨벤션** |
| [빠른 시작](getting-started/setup.md) | 개발 환경 설정, Docker 실행, 검증 체크리스트 |
| [도커 가이드](getting-started/docker-guide.md) | Docker Compose 명령어, 서비스별 설명, Docker Hub 워크플로우 |

## 아키텍처 (Architecture)

| 문서 | 설명 |
|------|------|
| [시스템 개요](architecture/overview.md) | 시스템 구조, 디렉토리 구조, 팀 간 의존성 |
| [챗봇 설계](architecture/chatbot-design.md) | LangGraph 기반 튜터 에이전트 설계 |
| [프론트엔드](architecture/frontend.md) | React 19 + Vite 프론트엔드 아키텍처 |

## 역할별 가이드 (Team Guides)

| 파트 | 담당자 | 가이드 |
|------|--------|--------|
| 프론트엔드 | 손영진 | [A_프론트엔드_손영진](team-guides/A_프론트엔드_손영진.md) |
| 백엔드 | 허진서 | [B_백엔드_허진서](team-guides/B_백엔드_허진서.md) |
| 챗봇 | 정지훈 | [C_챗봇_정지훈](team-guides/C_챗봇_정지훈.md) |
| 파이프라인 | 안례진 | [D_파이프라인_안례진](team-guides/D_파이프라인_안례진.md) |
| 인프라 | 도형준 | [E_인프라_도형준](team-guides/E_인프라_도형준.md) |

## 인프라 (Infrastructure)

- [인프라 구성](../infra/README.md) — 서버 역할, 배포 절차, Docker 태그 정책, 모니터링
- [LXD 서버 인벤토리](../lxd/inventory.md) — 인스턴스 목록, 스펙, 배포 현황

## STAR 리포트 (Star Reports)

| 담당자 | 리포트 |
|--------|--------|
| 손영진 | [YJ99Son](star-reports/YJ99Son.md) |
| 정지훈 | [J2hoon10](star-reports/J2hoon10.md) |
| 안례진 | [ryejinn](star-reports/ryejinn.md) |
| 허진서 | [jjjh02](star-reports/jjjh02.md) |
| 도형준 | [dorae222](star-reports/dorae222.md) |

## 참조 (Reference)

- [PRD](reference/prd.md) - 제품 요구사항 명세서
- [변경 이력](reference/changelog.md)
- [DB 스키마](reference/schema.dbml)
- [KIS API](reference/kis-api.md)
- [환경변수](reference/env-vars.md)
- [LLM 모델](reference/llm-models.md)
- [분석 시스템 (Analytics)](reference/analytics.md) — Clarity + PostHog + 자체 DB 통합 가이드
- [공용 계정 관리](reference/shared-accounts.md) — 외부 서비스 접속 정보, API Key 관리
- [변경이력 (changes/)](../changes/) — 팀원별 Phase 단위 상세 변경이력

## 아카이브 (Archive)

완료된 설계 문서:
- [챗봇 컨텍스트 재설계](archive/chatbot_context_redesign_plan.md)
- [챗봇 LangGraph 구조](archive/chatbot_langgraph_structure.md)
- [가드레일 검증 계획](archive/guardrail_verification_plan.md)
