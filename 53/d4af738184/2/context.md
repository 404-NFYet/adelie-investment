# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# LocalStack LXD 서버 구축 + Terraform 검증 + AWS 코드 브랜치 분리

## Context

AWS 인프라 코드(Terraform 7모듈, LocalStack, IAM 권한서, 가이드 12문서)가 `develop`에 존재하지만 한 번도 실행/검증된 적 없음. 현재 운영은 LXD + Docker + MinIO.

**목표**: LocalStack 전용 LXD 인스턴스를 생성하여 Terraform 코드를 실제 검증하고, AWS 인프라 코드를 develop에서 분리하여 별도 브랜치로 �...

### Prompt 2

LXD 호스트에서 Step 3~5 실행해줘

