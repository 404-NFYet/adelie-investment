# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# 포트폴리오 수익률 수정 + AI 튜터 복구 + 용어 하이라이팅 + 챗봇 버튼 수정

## Context

5가지 작업 통합:
1. **포트폴리오 수익률**: 보상 포인트가 수익률에 포함되는 버그 수정
2. **AI 튜터 복구**: OpenAI 쿼터 초과 → Anthropic fallback 추가 + Auth 헤더 누락 수정
3. **챗봇 응답 테스트**: 수정 후 실제 동작 검증
4. **용어 하이라이팅 복구**: 용어 설명 API가 OpenAI 의...

### Prompt 2

해결이 완료되었는가?

### Prompt 3

커밋하고 배포해줘

### Prompt 4

Base directory for this skill: /home/hj/2026/project/adelie-investment/.claude/skills/deploy

# Deploy Skill

서비스를 빌드하고 deploy-test 서버에 배포합니다.

## 사용법

`/deploy all`

- `/deploy frontend` — 프론트엔드만 빌드 + 푸시 + 배포
- `/deploy api` — FastAPI 백엔드만 빌드 + 푸시 + 배포
- `/deploy all` — 전체 서비스 빌드 + 푸시 + 배포
- `/deploy` (인자 없음) — 변경된 서비스 자동 감지 후 배포

## 서버 경로 (�...

