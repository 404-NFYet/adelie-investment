# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# 브랜치 정리 + Docker 이미지 전략: prod-final 기반 재설정

## Context

**문제**: develop 기반 커밋 히스토리 발산 (104커밋), dev-final/* 각 107~118커밋 ahead, Docker `:latest` 태그 남용.
**목표**: `v1.2.1-stable-feb20` (091a1bb) 베이스로 클린 리셋 + **최신 datapipeline 코드만 보존** + Docker 태그 정책 정비.

**현재 상태 (검증 완료)**:
- deploy-test: `release/feb20-stable` 브랜치, `TAG=feb20-stabl...

### Prompt 2

데이터 수집 파이프라인이 지금 코드와 같은지 점검해라. 데이터는 배포 서버에서 아마 업데이트를 하고 싱크를 해서 가져와야할건데, 배포 서버 코드도 lxd 서버들과 싱크를 맞춰야할 것 같다.

### Prompt 3

[Request interrupted by user]

### Prompt 4

내가 수동으로 파이프라인을 실행했었기 때문에 시간을 불일치할 수도 있다.

### Prompt 5

Continue from where you left off.

### Prompt 6

다시 플랜을 반환해라.

### Prompt 7

[Request interrupted by user for tool use]

