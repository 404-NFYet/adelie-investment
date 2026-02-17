# Adelie Investment 문서

"History Repeats Itself" - AI 기반 금융 교육 플랫폼

## 시작하기 (Getting Started)

| 문서 | 설명 |
|------|------|
| [빠른 시작](getting-started/setup.md) | 개발 환경 설정, Docker 실행, 검증 체크리스트 |
| [도커 가이드](getting-started/docker-guide.md) | Docker Compose 명령어, 서비스별 설명, Docker Hub 워크플로우 |
| [워크플로우](getting-started/workflow.md) | Git 브랜치 전략, 커밋 규칙, PR 프로세스 |

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

- _(localstack-guide.md 등 추가 예정)_

## STAR 리포트 (Star Reports)

- _(개인별 STAR 리포트 추가 예정)_

## 참조 (Reference)

- [PRD](reference/prd.md) - 제품 요구사항 명세서
- [변경 이력](reference/changelog.md)
- [DB 스키마](reference/schema.dbml)
- [KIS API](reference/kis-api.md)
- [환경변수](reference/env-vars.md)
- [LLM 모델](reference/llm-models.md)
- [AWS 배포](aws/)
