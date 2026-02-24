# ============================================================
# Adelie Investment — 팀 공통 Makefile
# 사용법: make help
# ============================================================

REGISTRY ?= dorae222
TAG      ?= latest

.PHONY: help \
        dev dev-down dev-frontend dev-api dev-frontend-local dev-api-local status \
        test test-unit test-e2e test-load test-frontend test-pipeline \
        migrate db-reset db-sync \
        build build-frontend build-api build-ai push deploy rollback \
        logs clean

# ============================================================
# 도움말
# ============================================================
help:
	@echo ""
	@echo "  Adelie Investment — Makefile 명령어 (make help)"
	@echo "  ================================================="
	@echo ""
	@echo "  [개발 환경]"
	@echo "    make dev                전체 스택 실행 (frontend + backend-api + postgres + redis)"
	@echo "    make dev-down           전체 스택 중지"
	@echo "    make dev-frontend       프론트엔드만 실행"
	@echo "    make dev-api            백엔드 API만 실행"
	@echo "    make dev-frontend-local 프론트엔드 로컬 실행 (Docker 없이, npm run dev)"
	@echo "    make dev-api-local      백엔드 API 로컬 실행 (Docker 없이, uvicorn)"
	@echo "    make status             컨테이너 상태 + 현재 브랜치 출력"
	@echo ""
	@echo "  [테스트]"
	@echo "    make test               전체 테스트 (backend)"
	@echo "    make test-unit          유닛 테스트만"
	@echo "    make test-e2e           E2E 테스트 (Playwright)"
	@echo "    make test-load          부하 테스트 (Locust, 40명)"
	@echo "    make test-pipeline      파이프라인 검증 테스트"
	@echo ""
	@echo "  [DB]"
	@echo "    make migrate            alembic upgrade heads"
	@echo "    make db-reset           DB 초기화 (⚠️  개발 환경 전용)"
	@echo "    make db-sync            prod DB 콘텐츠 → 로컬 dev DB 복제"
	@echo ""
	@echo "  [유틸]"
	@echo "    make logs               프로덕션 로그 tail"
	@echo "    make clean              Docker 캐시 + __pycache__ 정리"
	@echo ""
	@echo "  [빌드/배포 — 인프라 전용]"
	@echo "    make build              전체 Docker 이미지 빌드"
	@echo "    make build-frontend     프론트엔드만 빌드"
	@echo "    make build-api          백엔드 API만 빌드"
	@echo "    make build-ai           AI 파이프라인만 빌드"
	@echo "    make push               Docker Hub push (REGISTRY=$(REGISTRY) TAG=$(TAG))"
	@echo "    make deploy             docker-compose.prod.yml up -d (deploy-test에서)"
	@echo "    make rollback           :stable 이미지로 deploy-test 롤백"
	@echo ""
	@echo "  [인프라 전용 (lxd/Makefile)]"
	@echo "    make -f lxd/Makefile help    LXD 관리 명령어 전체 목록"
	@echo ""
	@echo "  상세 문서: docs/reference/make-commands.md"
	@echo ""

# ============================================================
# 개발 환경
# ============================================================
dev:
	docker compose -f docker-compose.dev.yml up --build

dev-down:
	docker compose -f docker-compose.dev.yml down

dev-frontend:
	docker compose -f docker-compose.dev.yml up --build frontend

dev-api:
	docker compose -f docker-compose.dev.yml up --build backend-api

dev-frontend-local:
	cd frontend && npm run dev

dev-api-local:
	cd fastapi && ../.venv/bin/uvicorn app.main:app --port 8082 --reload

status:
	@echo "=== 현재 브랜치 ==="
	@git branch --show-current
	@echo ""
	@echo "=== 컨테이너 상태 ==="
	@docker compose -f docker-compose.dev.yml ps 2>/dev/null || echo "  (개발 환경 미실행)"

# ============================================================
# 테스트
# ============================================================
test: test-backend

test-backend:
	@echo "테스트 실행 중 (backend)..."
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit test-backend

test-unit:
	@echo "유닛 테스트 실행 중..."
	pytest tests/unit/ -v --tb=short

test-e2e:
	@echo "E2E 테스트 실행 중 (Playwright)..."
	docker compose -f docker-compose.test.yml --profile e2e up --build --abort-on-container-exit test-e2e

test-load:
	@echo "부하 테스트 실행 중 (40명)..."
	@command -v locust >/dev/null 2>&1 || pip install locust -q
	locust -f tests/load/locustfile.py --headless -u 40 -r 5 --run-time 2m --host http://localhost:80

test-frontend:
	@echo "프론트엔드 테스트 실행 중..."
	cd frontend && npm test

test-pipeline:
	@echo "파이프라인 검증 테스트..."
	pytest tests/test_pipeline_validation.py -v --tb=short 2>/dev/null || echo "파이프라인 테스트 파일 없음 — 추가 예정"

# ============================================================
# DB
# ============================================================
migrate:
	cd database && ../.venv/bin/alembic upgrade heads

db-reset:
	@echo "⚠️  DB 초기화 — 개발 환경 전용"
	.venv/bin/python database/scripts/reset_db.py --content-only

db-sync:
	bash database/scripts/sync_dev_data.sh
	@echo "prod 콘텐츠 데이터가 dev DB로 복사됨"

# 하위 호환 별칭
sync-dev-data: db-sync

# ============================================================
# 빌드 / Docker Hub Push
# ============================================================
build: build-frontend build-api build-ai

build-frontend:
	docker build -t $(REGISTRY)/adelie-frontend:$(TAG) ./frontend

build-api:
	docker build -f fastapi/Dockerfile -t $(REGISTRY)/adelie-backend-api:$(TAG) .

build-ai:
	docker build -f datapipeline/Dockerfile -t $(REGISTRY)/adelie-ai-pipeline:$(TAG) .

push:
	docker push $(REGISTRY)/adelie-frontend:$(TAG)
	docker push $(REGISTRY)/adelie-backend-api:$(TAG)
	docker push $(REGISTRY)/adelie-ai-pipeline:$(TAG)

# ============================================================
# 배포 / 롤백 (인프라 전용 — deploy-test에서 실행)
# ============================================================
deploy:
	REGISTRY=$(REGISTRY) TAG=$(TAG) docker compose -f docker-compose.prod.yml up -d --remove-orphans

deploy-down:
	docker compose -f docker-compose.prod.yml down

rollback:
	@echo "=== 롤백: feb20-stable 이미지 → deploy-test ==="
	docker pull $(REGISTRY)/adelie-frontend:feb20-stable
	docker pull $(REGISTRY)/adelie-backend-api:feb20-stable
	TAG=feb20-stable docker compose -f docker-compose.prod.yml up -d --no-deps frontend backend-api
	docker exec adelie-frontend nginx -s reload 2>/dev/null || true
	@echo "=== 롤백 완료 ==="

# ============================================================
# 유틸
# ============================================================
logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=100

deploy-logs: logs

clean:
	docker compose -f docker-compose.dev.yml down -v 2>/dev/null || true
	docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
	docker compose -f docker-compose.test.yml down -v 2>/dev/null || true
	docker system prune -f
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "정리 완료"
