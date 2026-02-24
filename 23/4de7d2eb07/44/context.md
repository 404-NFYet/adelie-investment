# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# 브랜치 전략 + CI/CD + Makefile 전면 재설계

## Context

**현재 문제:**
- `develop` push → 프로덕션 자동 배포 (staging/prod 구분 없음)
- `dev-final/*`는 CI/CD와 완전히 단절 (수동 git pull)
- `dev-final/*`가 `release/feb20-stable` 기반 — `develop`과 히스토리 분기
- `dev/*` 브랜치는 `dev-final/*`와 역할 중복, 미사용
- AWS 관련 워크플로우(`deploy-aws.yml`) 잔존
- Makefile 타겟이 산재해 팀원...

### Prompt 2

일회성 수동 작업까지 진행할 계획을 세워라.

### Prompt 3

[Request interrupted by user for tool use]

