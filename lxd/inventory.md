# LXD 서버 인벤토리

## 인스턴스 현황 (2026-02-24 업데이트)

| 인스턴스 | IP | 역할 | 담당자 | CPU/RAM | 프로파일 |
|----------|-----|------|--------|---------|---------|
| infra-server | 10.10.10.10 | PostgreSQL, Redis, MinIO | 공유 | 8/24GB | `infra.yml` |
| deploy-test | 10.10.10.20 | prod 배포 서버 | 도형준 | 16/32GB | `deploy.yml` |
| dev-yj99son | 10.10.10.14 | PM / Frontend | 손영진 | 4/8GB | `dev-standard.yml` |
| dev-j2hoon10 | 10.10.10.11 | Chatbot (LangGraph 에이전트) | 정지훈 | 4/12GB | `dev-ai.yml` |
| dev-ryejinn | 10.10.10.13 | Data Pipeline (LangGraph 파이프라인) | 안례진 | 4/12GB | `dev-ai.yml` |
| dev-jjjh02 | 10.10.10.12 | Backend (FastAPI, DB) | 허진서 | 4/8GB | `dev-standard.yml` |
| dev-hj | 10.10.10.15 | Infra (Docker, CI/CD) | 도형준 | 4/8GB | `dev-standard.yml` |
| **합계** | - | - | - | **44/104GB** | - |

> 디스크: 전체 인스턴스가 **1개의 1.8TB NVMe**를 공유하는 구조.

## 스토리지 Quota

| 인스턴스 | Quota | 비고 |
|----------|-------|------|
| infra-server | 300GB | PostgreSQL, Redis, MinIO 데이터 |
| deploy-test | 200GB | Docker 이미지 + 컨테이너 |
| dev-* (각각) | 150GB | 소스코드, Docker, node_modules |
| 예비 | 550GB | 향후 확장용 |

## 배포 현황 (2026-02-24 업데이트)

### deploy-test (10.10.10.20) — 통합 배포 서버

| 서비스 | 컨테이너 | 포트 | URL |
|--------|----------|------|-----|
| Frontend (nginx) | adelie-frontend | :80 | https://demo.adelie-invest.com |
| Backend API | adelie-backend-api | :8082 | (내부) |
| PostgreSQL | adelie-postgres | :5432 | (내부) |
| Redis | adelie-redis | :6379 | (내부) |
| Prometheus | adelie-prometheus | :9090 | (내부) |
| Grafana | adelie-grafana | :3000 | https://monitoring.adelie-invest.com |
| Streamlit Dashboard | adelie-dashboard | :8501 | https://dashboard.adelie-invest.com |

- Monitoring + Dashboard: `infra/monitoring/docker-compose.yml`
- Main app: `docker-compose.prod.yml`
- **git 브랜치**: `release/feb20-stable` (091a1bb)
- **이미지 태그**: `dorae222/adelie-frontend:feb20-stable`, `dorae222/adelie-backend-api:feb20-stable`
- **alembic HEAD**: `20260223_expires` (2026-02-24 수동 적용, DB는 최신 스키마 유지)
- **ai-pipeline**: `:feb20-stable` 미존재 → 기존 컨테이너 유지 또는 `:latest` 사용

### infra-server (10.10.10.10) — 로컬 SSH 접근 불가 (팀 내부망 전용)

## dev-final 브랜치 워크플로우 (2026-02-24 기준)

### 브랜치 구조 및 서버 현황

`release/feb20-stable` (091a1bb) 베이스 + 각 팀원 `dev/*` 브랜치를 머지한 최종 통합 브랜치.

| 브랜치 | HEAD | 서버 | 담당자 | 컨테이너 |
|--------|------|------|--------|---------|
| `dev-final/frontend` | 43d65d1 | dev-yj99son | 손영진 | ✅ Up |
| `dev-final/chatbot` | 4263e83 | dev-j2hoon10 | 정지훈 | ✅ Up |
| `dev-final/backend` | a809895 | dev-jjjh02 | 허진서 | ✅ Up |
| `dev-final/pipeline` | 5af539d | dev-ryejinn | 안례진 | ✅ Up |
| `dev-final/infra` | 33760e1 | dev-hj | 도형준 | ✅ Up |

각 서버 로컬 스택: `postgres` + `redis` + `backend-api` + `frontend` (docker-compose.dev.yml)

### LXD 서버 ↔ 브랜치 싱크 절차

```bash
# 1. dev-final/* 브랜치 생성/갱신 (release/feb20-stable + dev/* 머지 → origin push)
make -f lxd/Makefile dev-final-branches

# 2. 각 LXD 서버에서 해당 dev-final/* checkout
make -f lxd/Makefile dev-final-checkout

# 3. Docker 재빌드 + up -d
make -f lxd/Makefile dev-final-rebuild

# 전체 원스텝
make -f lxd/Makefile dev-final-setup
```

> **주의**: `dev-final/*` 브랜치는 반드시 `release/feb20-stable`을 베이스로 생성해야 함.
> `develop` 기반 이미지(`:latest`) 사용 금지 — 검증되지 않은 실험적 변경 포함.

### LXD 개발 DB 구성 (2026-02-24 변경)

기존: 모든 LXD → infra-server 공유 DB (10.10.10.10:5432)
**신규: 각 LXD 서버 → 개인 로컬 postgres (docker-compose.dev.yml postgres:5432)**

```bash
# 각 LXD 서버 로컬 DB 초기화 + prod 데이터 복제 (1회)
make -f lxd/Makefile dev-local-db-setup
```

- `docker-compose.dev.yml`의 `environment.DATABASE_URL: postgres:5432`가 `.env`보다 우선 적용
- 코드 변경 없이 자동으로 로컬 postgres 사용
- infra-server `tmp-postgres-1`은 계속 실행 중이나 LXD 개발 환경에서 더 이상 연결 안 함

## 역할 변경 이력

- 2026-02-24: localstack 인스턴스 제거 (AWS 전환 계획 보류)
- 2026-02-14: dev-ryejinn `dev-qa.yml` (2/4GB) → `dev-ai.yml` (4/12GB) 승격 (Pipeline 담당 전환)
- 2026-02-14: deploy-test RAM 64GB → 32GB 축소 (실사용 ~1.3GB 대비 과잉)

## 프로파일 적용 명령어

```bash
# dev-hj (인프라)
lxc config set dev-hj limits.cpu 4
lxc config set dev-hj limits.memory 8GB

# dev-j2hoon10 (Chatbot)
lxc config set dev-j2hoon10 limits.cpu 4
lxc config set dev-j2hoon10 limits.memory 12GB

# dev-jjjh02 (Backend)
lxc config set dev-jjjh02 limits.cpu 4
lxc config set dev-jjjh02 limits.memory 8GB

# dev-ryejinn (Pipeline) — 승격
lxc config set dev-ryejinn limits.cpu 4
lxc config set dev-ryejinn limits.memory 12GB

# dev-yj99son (Frontend)
lxc config set dev-yj99son limits.cpu 4
lxc config set dev-yj99son limits.memory 8GB

# deploy-test (prod 배포)
lxc config set deploy-test limits.memory 32GB

# 스토리지 quota (pool: default)
for inst in infra-server deploy-test dev-hj dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-yj99son; do
  echo "$inst: $(lxc config device get $inst root size 2>/dev/null || echo 'unset')"
done
```

> 프로파일 적용 전 팀원 공지 필수. 실행 중인 작업 확인 후 적용.
