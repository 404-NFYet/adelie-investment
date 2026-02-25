# test-server (10.10.10.19) staging 환경 아카이브

> **아카이브 날짜**: 2026-02-24
> **사유**: staging 환경 혼동 방지를 위해 코드베이스에서 참조 제거. 프로덕션은 `deploy-test` (10.10.10.20, demo.adelie-invest.com) 단일 운영.

---

## inventory.md 백업

### 인스턴스 행

| 인스턴스 | IP | 역할 | 담당자 | CPU/RAM | 프로파일 |
|----------|-----|------|--------|---------|---------|
| test-server | 10.10.10.19 | staging 배포 서버 (test.adelie-invest.com) | 도형준 | 8/16GB | custom |

### 배포 현황 섹션

#### test-server (10.10.10.19) — staging 배포 서버

| 서비스 | 컨테이너 | 포트 | URL |
|--------|----------|------|-----|
| Frontend (nginx) | adelie-frontend | :80 | https://test.adelie-invest.com |
| Backend API | adelie-backend-api | :8082 | (내부) |
| PostgreSQL | adelie-postgres | :5432 | (내부) |
| Redis | adelie-redis | :6379 | (내부) |

- 기준 브랜치: `release/feb20-stable` (091a1bb)
- 이미지 태그: `dorae222/adelie-*:feb20-stable`
- 파이프라인 스케줄러: **비활성화** (staging 전용)
- Main app: `docker-compose.prod.yml`

---

## Makefile 백업

### deploy-staging 타겟

```makefile
# --- Staging (test-server, 10.10.10.19) ---
# test.adelie-invest.com — release/feb20-stable 기준 독립 환경
STAGING_TAG ?= feb20-stable

deploy-staging:
	@echo "=== test-server(10.10.10.19) staging 배포 ==="
	lxc exec test-server -- bash -c '\
		cd /root/adelie-investment && \
		git pull origin release/feb20-stable && \
		docker compose -f docker-compose.prod.yml pull && \
		docker compose -f docker-compose.prod.yml up -d --remove-orphans && \
		docker exec adelie-frontend nginx -s reload 2>/dev/null || true'
	@echo "=== staging 배포 완료 ==="
```

### health-staging 타겟

```makefile
health-staging:
	@echo "=== test-server(10.10.10.19) 헬스체크 ==="
	@lxc exec test-server -- bash -c '\
		echo "  브랜치: $$(cd /root/adelie-investment && git branch --show-current 2>/dev/null)"; \
		echo "  컨테이너:"; \
		cd /root/adelie-investment && \
		docker compose -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | tail -n +2 | \
			awk "{printf \"    %-35s %s\\n\", \$$1, \$$2}"; \
		echo "  API 헬스:"; \
		curl -s http://localhost:8082/api/v1/health 2>/dev/null | head -1 || echo "    ❌ API 미응답"'
	@echo "=== 헬스체크 완료 ==="
```

---

# localstack (10.10.10.16) 아카이브

> **아카이브 날짜**: 2026-02-24
> **사유**: AWS 로컬 테스트 환경 미사용으로 LXC 컨테이너 삭제 및 코드베이스 참조 제거.

## inventory.md 백업

### 인스턴스 행

| 인스턴스 | IP | 역할 | 담당자 | CPU/RAM | 프로파일 |
|----------|-----|------|--------|---------|---------|
| localstack | 10.10.10.16 | LocalStack (AWS 로컬 테스트) | 도형준 | 4/8GB | `dev-standard.yml` |

### 스토리지 Quota

| 인스턴스 | Quota | 비고 |
|----------|-------|------|
| localstack | 100GB | Docker 이미지, Terraform state, LocalStack 데이터 |

### 프로파일 적용 명령어

```bash
# localstack (AWS 로컬 테스트)
lxc config set localstack limits.cpu 4
lxc config set localstack limits.memory 8GB
```
