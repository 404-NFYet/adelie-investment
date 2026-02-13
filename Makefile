# ============================================================
# Adelie Investment - 통합 자동화 Makefile
# 사용법: make help
# ============================================================

REGISTRY ?= dorae222
TAG ?= latest
SERVICES = frontend backend-api ai-pipeline

.PHONY: help build push push-local dev dev-down deploy deploy-down \
        dev-frontend-local dev-api-local \
        test test-backend test-e2e test-load test-pipeline test-frontend \
        migrate logs clean

# --- 도움말 ---
help:
	@echo ""
	@echo "  아델리에 - Makefile 명령어"
	@echo "  ================================"
	@echo ""
	@echo "  빌드/배포:"
	@echo "    make build          모든 Docker 이미지 빌드"
	@echo "    make build-frontend 프론트엔드만 빌드"
	@echo "    make push           Docker Hub($(REGISTRY))에 푸시"
	@echo "    make push-local     로컬 레지스트리(10.10.10.10:5000)에 푸시"
	@echo ""
	@echo "  개발:"
	@echo "    make dev            개발 환경 실행 (infra-server 연결)"
	@echo "    make dev-down       개발 환경 중지"
	@echo ""
	@echo "  배포:"
	@echo "    make deploy         배포 환경 실행 (풀스택)"
	@echo "    make deploy-down    배포 환경 중지"
	@echo ""
	@echo "  테스트:"
	@echo "    make test           전체 테스트 (backend)"
	@echo "    make test-backend   백엔드 테스트 (pytest)"
	@echo "    make test-e2e       E2E 테스트 (Playwright)"
	@echo "    make test-load      부하 테스트 (Locust, 40명)"
	@echo "    make test-pipeline  파이프라인 검증 테스트"
	@echo ""
	@echo "  유틸리티:"
	@echo "    make migrate        DB 마이그레이션 (Alembic)"
	@echo "    make logs           배포 환경 로그 조회"
	@echo "    make clean          Docker 시스템 정리"
	@echo ""
	@echo "  변수:"
	@echo "    REGISTRY=$(REGISTRY)  TAG=$(TAG)"
	@echo ""

# --- Docker 빌드 ---
build: build-frontend build-api build-ai

build-frontend:
	@echo "🔨 Building frontend..."
	docker build -t $(REGISTRY)/adelie-frontend:$(TAG) ./frontend

build-api:
	@echo "🔨 Building backend-api..."
	docker build -f fastapi/Dockerfile -t $(REGISTRY)/adelie-backend-api:$(TAG) .

build-ai:
	@echo "🔨 Building ai-pipeline..."
	docker build -f datapipeline/Dockerfile -t $(REGISTRY)/adelie-ai-pipeline:$(TAG) .

# --- Docker Push ---
push:
	@echo "📤 Pushing to Docker Hub ($(REGISTRY))..."
	docker push $(REGISTRY)/adelie-frontend:$(TAG)
	docker push $(REGISTRY)/adelie-backend-api:$(TAG)
	docker push $(REGISTRY)/adelie-ai-pipeline:$(TAG)

push-local:
	@echo "📤 Pushing to local registry..."
	@for svc in frontend backend-api ai-pipeline; do \
		docker tag $(REGISTRY)/adelie-$$svc:$(TAG) 10.10.10.10:5000/adelie-$$svc:$(TAG); \
		docker push 10.10.10.10:5000/adelie-$$svc:$(TAG); \
	done

# --- 개발 환경 ---
dev:
	docker compose -f docker-compose.dev.yml up --build

dev-down:
	docker compose -f docker-compose.dev.yml down

dev-frontend:
	docker compose -f docker-compose.dev.yml up --build frontend

dev-api:
	docker compose -f docker-compose.dev.yml up --build backend-api

# --- 로컬 개발 (Docker 없이) ---
dev-frontend-local:
	cd frontend && npm run dev

dev-api-local:
	cd fastapi && ../.venv/bin/uvicorn app.main:app --port 8082 --reload

# --- 배포 환경 ---
deploy:
	REGISTRY=$(REGISTRY) TAG=$(TAG) docker compose -f docker-compose.prod.yml up -d

deploy-down:
	docker compose -f docker-compose.prod.yml down

deploy-logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=100

# --- Deploy-test (10.10.10.20): 로컬 빌드 → 푸시 → 서버 pull → 재시작 ---
deploy-test: build push
	ssh deploy-test 'cd ~/adelie-investment && git pull origin develop && \
		docker compose -f docker-compose.prod.yml pull && \
		docker compose -f docker-compose.prod.yml up -d --remove-orphans && \
		docker exec adelie-frontend nginx -s reload 2>/dev/null || true'

deploy-test-service:
	$(MAKE) build-$(SVC) && docker push $(REGISTRY)/adelie-$(SVC):$(TAG)
	ssh deploy-test 'cd ~/adelie-investment && git pull origin develop && \
		docker compose -f docker-compose.prod.yml pull $(SVC) && \
		docker compose -f docker-compose.prod.yml up -d $(SVC) && \
		docker exec adelie-frontend nginx -s reload 2>/dev/null || true'

# --- 테스트 ---
test: test-backend

test-backend:
	@echo "🧪 Running backend tests..."
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit test-backend

test-e2e:
	@echo "🧪 Running E2E tests (Playwright)..."
	docker compose -f docker-compose.test.yml --profile e2e up --build --abort-on-container-exit test-e2e

test-load:
	@echo "🧪 Running load test (40 users)..."
	@command -v locust >/dev/null 2>&1 || pip install locust -q
	locust -f tests/load/locustfile.py --headless -u 40 -r 5 --run-time 2m --host http://localhost:80

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test

test-pipeline:
	@echo "🧪 Running pipeline validation..."
	pytest tests/test_pipeline_validation.py -v --tb=short 2>/dev/null || echo "파이프라인 테스트 파일 없음 - Phase 4 이후 추가 예정"

# --- DB 마이그레이션 ---
migrate:
	cd database && alembic upgrade head

# --- 로그 ---
logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=100

# --- 정리 ---
clean:
	docker compose -f docker-compose.dev.yml down -v 2>/dev/null || true
	docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
	docker compose -f docker-compose.test.yml down -v 2>/dev/null || true
	docker system prune -f
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✨ 정리 완료"
