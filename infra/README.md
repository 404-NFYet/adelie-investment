# Adelie — 인프라 구성 (2026-02-25 기준)

## 서버 역할

### deploy-test (10.10.10.20) — 프로덕션 서버

완전 독립 스택. git 브랜치: `prod-final`.

| 서비스 | 컨테이너 | 포트 | 비고 |
|--------|----------|------|------|
| Frontend (nginx) | adelie-frontend | :80 | SPA + API 리버스 프록시 |
| Backend API | adelie-backend-api | :8082 | FastAPI |
| PostgreSQL 16 (pgvector) | adelie-postgres | :5432 | 내부 전용 |
| Redis 7 | adelie-redis | :6379 | 캐싱, Rate Limiting |
| MinIO | adelie-minio | :9000/:9001 | S3 호환 오브젝트 스토리지 |
| Prometheus | adelie-prometheus | :9090 | 메트릭 수집 |
| Grafana | adelie-grafana | :3000 | 모니터링 대시보드 |
| cAdvisor | adelie-cadvisor | :8080 | 컨테이너 메트릭 |
| Alertmanager | adelie-alertmanager | :9093 | 알림 관리 |
| Streamlit | adelie-dashboard | :8501 | nginx 프록시 경유 |

- Main app: `docker-compose.prod.yml`
- Monitoring + Dashboard: `infra/monitoring/docker-compose.yml`

### infra-server (10.10.10.10) — 모니터링 에이전트

deploy-test Prometheus가 스크레이핑하는 메트릭 수집 에이전트만 운영.

| 서비스 | 포트 | 상태 |
|--------|------|------|
| cAdvisor | :8080 | 운영 중 — 컨테이너 메트릭 수집 |
| node_exporter | :9100 | 운영 중 — 시스템 메트릭 수집 |
| tmp-postgres-1 | :5432 | 레거시 — 실행 중이나 미사용 (2026-02-24 개인 로컬 DB로 전환) |
| tmp-redis-1 | :6379 | 레거시 — 실행 중이나 미사용 |

### dev-* 서버 — 개인 개발 환경 (LXD)

각 서버가 `docker-compose.dev.yml`로 로컬 PostgreSQL을 운영.

```bash
# 초기 세팅 (기동 + 마이그레이션 + prod 데이터 복제 + 재시작)
make -f lxd/Makefile dev-local-db-setup

# prod 데이터 최신화
make -f lxd/Makefile sync-dev-data
```

서버 목록: `lxd/inventory.md` 참조.

## 서비스 URL

| URL | 서비스 | 비고 |
|-----|--------|------|
| https://demo.adelie-invest.com | Frontend (nginx) | Cloudflare Tunnel → deploy-test:80 |
| https://monitoring.adelie-invest.com | Grafana | Cloudflare Tunnel → deploy-test:3000 |
| https://dashboard.adelie-invest.com | Streamlit 대시보드 | Cloudflare Tunnel → deploy-test:8501 (nginx) |
| https://analytics.adelie-invest.com | PostHog (분석) | Cloudflare Tunnel → analytics LXD (10.10.10.17) |

## 배포 절차

```bash
# 1. 빌드
make build                  # frontend + backend-api 이미지 빌드

# 2. Docker Hub 푸시
make push                   # dorae222/adelie-* 이미지 푸시

# 3. deploy-test 배포
make deploy                 # SSH → docker compose pull + up -d
```

또는 개별 서비스:

```bash
make build-frontend && make push    # 프론트엔드만
make build-api && make push         # 백엔드만
```

## Docker 이미지 태그 정책

- `:latest` **사용 중지** (2026-02-24~)
- 배포 태그: `prod-YYYYMMDD` (예: `prod-20260224`)
- 기준선 태그: `feb20-stable` (v1.2.1-stable-feb20 스냅샷)
- `docker-compose.prod.yml`에 `TAG` 환경변수로 태그 지정

```bash
# deploy-test에서
TAG=prod-20260225 docker compose -f docker-compose.prod.yml up -d
```

## 모니터링 스택

`infra/monitoring/` 디렉토리에서 관리.

| 구성 요소 | 파일 |
|-----------|------|
| Prometheus | `prometheus.yml` — 스크레이프 타겟 (deploy-test + infra-server) |
| Alertmanager | `alertmanager.yml` — Discord 알림 |
| 알림 규칙 | `rules/adelie-alerts.yml` |
| Grafana 대시보드 | Grafana UI에서 관리 |

```bash
# 모니터링 스택 재시작
ssh deploy-test 'cd ~/adelie-investment/infra/monitoring && docker compose up -d'
```

## 리소스 요약 (deploy-test 기준)

| 서비스 | Memory | 비고 |
|--------|--------|------|
| PostgreSQL | 4G | pgvector 포함 |
| Redis | 512MB | allkeys-lru |
| MinIO | 1G | |
| Backend API | ~1G | FastAPI + uvicorn |
| Frontend | ~256MB | nginx |
| 모니터링 (4개) | ~2G | Prometheus + Grafana + cAdvisor + Alertmanager |
| Streamlit | ~512MB | nginx + dashboard |

## 상태 확인

```bash
# deploy-test 전체 서비스 상태
ssh deploy-test 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# PostgreSQL 헬스체크
ssh deploy-test 'docker exec adelie-postgres pg_isready -U narative -d narrative_invest'

# Redis 핑
ssh deploy-test 'docker exec adelie-redis redis-cli ping'

# LXD 서버 전체 헬스체크
make -f lxd/Makefile health-lxd
```

## 문제 해결

### 컨테이너 로그 확인

```bash
ssh deploy-test 'docker logs --tail 100 adelie-backend-api'
ssh deploy-test 'docker logs --tail 100 adelie-frontend'
ssh deploy-test 'docker logs --tail 100 adelie-postgres'
```

### 서비스 재시작

```bash
# 개별 서비스
ssh deploy-test 'cd ~/adelie-investment && docker compose -f docker-compose.prod.yml restart backend-api'

# 전체 재시작
ssh deploy-test 'cd ~/adelie-investment && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d'
```

### DB 마이그레이션

```bash
# deploy-test
ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'

# 로컬 (LXD dev)
cd database && ../.venv/bin/alembic upgrade head
```

### 데이터 초기화 (주의: 데이터 삭제됨)

```bash
ssh deploy-test 'cd ~/adelie-investment && docker compose -f docker-compose.prod.yml down -v'
ssh deploy-test 'cd ~/adelie-investment && docker compose -f docker-compose.prod.yml up -d'
```
