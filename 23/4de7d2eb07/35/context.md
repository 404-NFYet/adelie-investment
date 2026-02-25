# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# test-server (10.10.10.19) staging 환경 참조 제거

## Context
`test.adelie-invest.com` (10.10.10.19, LXC `test-server`)은 staging 배포 서버로, 프로덕션 `demo.adelie-invest.com` (10.10.10.20, SSH `deploy-test`)과 별개로 운영되었다. 혼동 방지를 위해 test-server 관련 참조를 코드베이스에서 제거하되, 내용은 아카이브로 백업한다.

## 영향 범위 (2개 파일만 해당)

| 파일 | 제거 대상 |
|------|-----...

### Prompt 2

lxd 서버까지 모두 제거하였는가?

### Prompt 3

컨테이너도 정리해라

### Prompt 4

localstack도 제거해라.

