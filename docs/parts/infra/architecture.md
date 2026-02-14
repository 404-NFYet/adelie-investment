# Infra 아키텍처

> LXD 인스턴스, Docker Compose 구성, Cloudflare Tunnel, GitHub Actions, Docker Hub 태깅, SSH ProxyJump를 다룬다.

---

## LXD 인스턴스 (7개)

모든 인스턴스는 1대의 물리 서버 위에서 LXD로 운영된다. 1.8TB NVMe 공유 스토리지.

| 인스턴스 | IP | 역할 | 담당자 | CPU/RAM | 프로파일 | Disk Quota |
|----------|-----|------|--------|---------|---------|-----------|
| infra-server | 10.10.10.10 | 공유 인프라 (DB, Redis, MinIO, 모니터링) | 공유 | 8/24GB | `infra.yml` | 300GB |
| deploy-test | 10.10.10.20 | prod 배포 (Docker Compose fullstack) | 도형준 | 16/32GB | `deploy.yml` | 200GB |
| dev-yj99son | 10.10.10.14 | PM / Frontend | 손영진 | 4/8GB | `dev-standard.yml` | 150GB |
| dev-j2hoon10 | 10.10.10.11 | Chatbot (LangGraph 에이전트) | 정지훈 | 4/12GB | `dev-ai.yml` | 150GB |
| dev-ryejinn | 10.10.10.13 | Data Pipeline (LangGraph 파이프라인) | 안례진 | 4/12GB | `dev-ai.yml` | 150GB |
| dev-jjjh02 | 10.10.10.12 | Backend (FastAPI, DB) | 허진서 | 4/8GB | `dev-standard.yml` | 150GB |
| dev-hj | 10.10.10.15 | Infra (Docker, CI/CD) | 도형준 | 4/8GB | `dev-standard.yml` | 150GB |

### 프로파일 구분

| 프로파일 | CPU | RAM | 대상 |
|---------|-----|-----|------|
| `infra.yml` | 8 | 24GB | infra-server (DB, Redis 등) |
| `deploy.yml` | 16 | 32GB | deploy-test (Docker fullstack) |
| `dev-standard.yml` | 4 | 8GB | 일반 개발 (Frontend, Backend, Infra) |
| `dev-ai.yml` | 4 | 12GB | AI 개발 (Chatbot, Pipeline — LLM 클라이언트 메모리) |

### 리소스 변경 명령

```bash
# 예: dev-ryejinn RAM 변경
lxc config set dev-ryejinn limits.memory 12GB
```

리소스 변경 전 반드시 팀원에게 공지하고, 실행 중인 작업 확인 후 적용한다.

---

## Docker Compose 파일 구성

### 파일 목록

| 파일 | 용도 | 서비스 |
|------|------|--------|
| `docker-compose.dev.yml` | 로컬 개발 | postgres, redis, frontend, backend-api, ai-pipeline(profile), db-migrate |
| `docker-compose.prod.yml` | deploy-test 배포 | postgres, redis, minio, frontend, backend-api, ai-pipeline(profile) |
| `docker-compose.test.yml` | 테스트 | pytest 실행 |
| `infra/docker-compose.yml` | infra-server | postgres, redis, neo4j, minio |
| `infra/monitoring/docker-compose.yml` | 모니터링 | prometheus, grafana |

### docker-compose.dev.yml

```
services:
  postgres    (postgres:15)                localhost:5433
  redis       (redis:7-alpine)             localhost:6379
  frontend    (빌드: ./frontend)           localhost:3001
  backend-api (빌드: ./fastapi/Dockerfile) localhost:8082
  ai-pipeline (profile: pipeline)          수동 실행
  db-migrate  (alembic upgrade heads)      1회성
```

볼륨 마운트: `fastapi/app`, `chatbot/`, `datapipeline/` → 핫 리로드 지원

### docker-compose.prod.yml

```
services:
  postgres    (pgvector/pgvector:pg16)     내부 5432
  redis       (redis:7-alpine)             내부 6379
  minio       (minio/minio:latest)         내부 9000, 9001
  frontend    (dorae222/adelie-frontend)   :80 → 외부 공개
  backend-api (dorae222/adelie-backend-api) :8082 (expose only)
  ai-pipeline (dorae222/adelie-ai-pipeline) profile: pipeline
```

환경변수: `.env` 파일에서 로드 + `environment` 섹션으로 오버라이드 (DATABASE_URL, REDIS_URL 등)

---

## infra-server 인프라 서비스

`infra/docker-compose.yml`에서 관리하는 공유 서비스:

| 서비스 | 이미지 | 포트 | 메모리 | 용도 |
|--------|--------|------|--------|------|
| PostgreSQL 16 | `pgvector/pgvector:pg16` | 5432 | 4G | 메인 DB + pgvector |
| Redis 7 | `redis:7-alpine` | 6379 | 1G | 캐싱, 세션, Rate Limiting |
| Neo4j 5 | `neo4j:5-community` | 7474, 7687 | 4G | 기업 관계 그래프 |
| MinIO | `minio/minio:latest` | 9000, 9001 | 1G | 오브젝트 스토리지 (리포트 PDF) |

모든 서비스는 `narrative-network`에서 통신한다.

---

## Cloudflare Tunnel

외부 접근을 위해 Cloudflare Tunnel을 사용한다.

| 도메인 | 대상 | 용도 |
|--------|------|------|
| `demo.adelie-invest.com` | deploy-test:80 (frontend) | 서비스 데모 |
| `monitoring.adelie-invest.com` | infra-server:3000 (grafana) | 모니터링 대시보드 |

설정 스크립트: `infra/setup-cloudflare-tunnel.sh`

---

## GitHub Actions

### Discord Notification (`.github/workflows/main.yml`)

모든 push에 Discord Webhook으로 알림을 전송한다.

| 브랜치 | 색상 | 제목 |
|--------|------|------|
| `prod` | 빨강 | 프로덕션 배포 |
| `develop` | 주황 | 통합 브랜치 업데이트 |
| `dev/*` | 파랑 | 개인 작업 푸시 |
| `main` | 회색 | 문서 업데이트 |
| `hotfix/*` | 빨강 | 긴급 수정 |

### Claude Code Review (`.github/workflows/claude-code-review.yml`)

PR에 대해 Claude 기반 코드 리뷰를 자동으로 수행한다.

---

## Docker Hub 태깅

레지스트리: `dorae222/adelie-*`

| 이미지 | Dockerfile |
|--------|-----------|
| `dorae222/adelie-frontend` | `frontend/Dockerfile` (context: `./frontend`) |
| `dorae222/adelie-backend-api` | `fastapi/Dockerfile` (context: `.`) |
| `dorae222/adelie-ai-pipeline` | `datapipeline/Dockerfile` (context: `.`) |

### 태그 규칙

| Git 이벤트 | Docker 태그 | 명령어 |
|------------|------------|--------|
| develop → prod 머지 | `latest` | `make build && make push` |
| prod 태그 (v*) | `v{M.m.p}` | `make build TAG=v0.9.1 && make push TAG=v0.9.1` |
| 개발 중 테스트 | `dev-{SHA}` | `make build TAG=dev-$(git rev-parse --short HEAD)` |

### 빌드 명령어

```bash
make build                    # 모든 이미지 빌드 (latest)
make build-frontend           # 프론트엔드만
make build-api                # 백엔드 API만
make push                     # Docker Hub 푸시
make build TAG=v1.0.0         # 특정 태그로 빌드
make deploy                   # deploy-test 배포
```

---

## SSH ProxyJump

모든 LXD 인스턴스는 호스트 서버(`hj-server`)를 경유하여 접속한다.

### ~/.ssh/config 구성 (예시)

```
Host hj-server
    HostName <호스트 서버 IP>
    User hj

Host infra-server
    HostName 10.10.10.10
    User ubuntu
    ProxyJump hj-server

Host deploy-test
    HostName 10.10.10.20
    User ubuntu
    ProxyJump hj-server

Host dev-ryejinn
    HostName 10.10.10.13
    User ubuntu
    ProxyJump hj-server

# 이하 dev-* 동일 패턴
```

### 포트 포워딩

```bash
# Frontend(:3001) + Backend(:8082) 동시 포워딩
ssh -L 3001:localhost:3001 -L 8082:localhost:8082 dev-{name}

# DB 포트 포워딩 (원격 DB 접속)
ssh -L 15432:localhost:5432 deploy-test -N &
```

---

## Makefile 주요 타겟

| 타겟 | 설명 |
|------|------|
| `make dev` | Full stack 개발 환경 (docker-compose.dev.yml) |
| `make dev-frontend` | Frontend만 |
| `make dev-api` | Backend API만 |
| `make dev-down` | 개발 환경 중지 |
| `make build` | Docker 이미지 빌드 |
| `make push` | Docker Hub 푸시 |
| `make deploy` | deploy-test 배포 |
| `make test` | Backend 단위 테스트 |
| `make test-e2e` | Playwright E2E |
| `make test-load` | Locust 부하 테스트 |
| `make migrate` | Alembic migration 적용 |

---

## 네트워크 구성

```
인터넷
  ↓ Cloudflare Tunnel
  ├── demo.adelie-invest.com      → deploy-test:80 (frontend nginx)
  └── monitoring.adelie-invest.com → infra-server:3000 (grafana)

LXD 내부 네트워크 (10.10.10.0/24)
  ├── infra-server (.10)  — PostgreSQL:5432, Redis:6379, MinIO:9000, Prometheus:9090, Grafana:3000
  ├── deploy-test  (.20)  — frontend:80, backend-api:8082
  └── dev-*        (.11~.15) — 개발 환경
```
