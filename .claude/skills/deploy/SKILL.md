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
- `/deploy all` — 전체 서비스 빌드 + 푸시 + 배포
- `/deploy` (인자 없음) — 변경된 서비스 자동 감지 후 배포

## 서버 경로 (중요)

| 환경 | 프로젝트 경로 |
|------|--------------|
| **deploy-test (10.10.10.20)** | `~/adelie-investment` |
| **로컬 개발** | `/home/hj/2026/project/adelie-investment` |

## Docker 이미지 태깅 규칙

### 이미지 목록

| 서비스 | 이미지명 | 빌드 명령 |
|--------|---------|-----------|
| Frontend | `dorae222/adelie-frontend` | `make build-frontend` |
| Backend API | `dorae222/adelie-backend-api` | `make build-api` |
| AI Pipeline | `dorae222/adelie-ai-pipeline` | `make build-ai` |

### 태그 규칙

| 태그 | 용도 | 예시 |
|------|------|------|
| `latest` | 기본값, deploy-test 배포용 | `dorae222/adelie-frontend:latest` |
| `YYYYMMDD` | 날짜 기반 스냅샷 (릴리스 시) | `dorae222/adelie-frontend:20260214` |
| `v{N}` | 프로덕션 릴리스 버전 | `dorae222/adelie-frontend:v1` |

- 일반 배포: `make build push` (latest 태그 자동 사용)
- 태그 지정 배포: `TAG=20260214 make build push`
- deploy-test의 docker-compose.prod.yml은 `latest` 태그를 참조

## 실행 절차

### 전체 배포 (`/deploy all`)
```bash
# 1. 빌드
make build-frontend
make build-api

# 2. Docker Hub 푸시
make push

# 3. deploy-test 서버 배포
ssh deploy-test "cd ~/adelie-investment && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"

# 4. 상태 확인
ssh deploy-test "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### 단일 서비스 배포 (`/deploy frontend` 또는 `/deploy api`)
```bash
# frontend 예시
make build-frontend
docker push dorae222/adelie-frontend:latest
ssh deploy-test "cd ~/adelie-investment && docker compose -f docker-compose.prod.yml pull frontend && docker compose -f docker-compose.prod.yml up -d frontend"
```

### 원스텝 배포 (Makefile)
```bash
make deploy-test        # 전체: build → push → 서버 pull → up
SVC=frontend make deploy-test-service  # 단일 서비스
```

## 서비스 의존 순서

```
postgres (healthy) → redis (healthy) → backend-api (healthy) → frontend
                                     → minio
```

`docker compose up -d`는 healthcheck 기반으로 순서를 자동 관리한다.

## 배포 후 검증

```bash
# 1. 컨테이너 상태 확인
ssh deploy-test "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# 2. API 헬스체크
ssh deploy-test "curl -sf http://localhost:8082/api/v1/health || echo FAIL"

# 3. 프론트엔드 접속 확인
ssh deploy-test "curl -sf -o /dev/null -w '%{http_code}' http://localhost:80"

# 4. 최근 로그 확인
ssh deploy-test "docker logs adelie-backend-api --tail 20"
ssh deploy-test "docker logs adelie-frontend --tail 20"
```

## 롤백

```bash
# 이전 이미지로 롤백 (Docker Hub에 이전 태그가 있는 경우)
ssh deploy-test "cd ~/adelie-investment && \
  docker compose -f docker-compose.prod.yml pull && \
  docker compose -f docker-compose.prod.yml up -d"

# 특정 태그로 롤백
TAG=20260213 ssh deploy-test "cd ~/adelie-investment && \
  REGISTRY=dorae222 TAG=20260213 docker compose -f docker-compose.prod.yml up -d"

# 긴급: 서비스만 재시작 (이미지 변경 없이)
ssh deploy-test "docker restart adelie-backend-api"
```

## 주의사항

- 배포 전 `git status`로 커밋되지 않은 변경 확인
- TAG를 명시하지 않으면 latest 태그 사용
- **서버 경로**: `~/adelie-investment` (절대 `~/adelie`가 아님)
- 에러 발생 시 `ssh deploy-test "docker logs adelie-{서비스} --tail 50"` 로 로그 확인
