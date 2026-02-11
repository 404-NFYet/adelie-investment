---
name: deploy
description: 서비스 빌드 및 배포
user_invocable: true
---

# Deploy Skill

서비스를 빌드하고 deploy-test 서버에 배포합니다.

## 사용법

`/deploy $ARGUMENTS`

- `/deploy frontend` — 프론트엔드만 빌드 + 푸시 + 배포
- `/deploy api` — FastAPI 백엔드만 빌드 + 푸시 + 배포
- `/deploy spring` — Spring Boot만 빌드 + 푸시 + 배포
- `/deploy all` — 전체 서비스 빌드 + 푸시 + 배포
- `/deploy` (인자 없음) — 변경된 서비스 자동 감지 후 배포

## 실행 절차

1. **빌드**: `make build-{서비스}` (TAG 지정 시 `TAG=xxx make build-{서비스}`)
2. **푸시**: `make push` (Docker Hub dorae222/adelie-* 이미지 푸시)
3. **배포**: `ssh deploy-test "cd ~/adelie && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"`

## 주의사항

- 배포 전 `git status`로 커밋되지 않은 변경 확인
- TAG를 명시하지 않으면 latest 태그 사용
- 배포 후 `ssh deploy-test "docker ps"` 로 컨테이너 상태 확인
- 에러 발생 시 `ssh deploy-test "docker logs adelie-{서비스} --tail 50"` 로 로그 확인
