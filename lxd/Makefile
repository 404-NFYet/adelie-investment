# ============================================================
# lxd/Makefile — 인프라 전용 (dorae222/hj 서버에서만 실행)
# 사용법: make -f lxd/Makefile <target>
# ============================================================

ROOT := $(realpath $(dir $(lastword $(MAKEFILE_LIST)))..)
REGISTRY ?= dorae222
TAG ?= latest

.PHONY: help push push-local deploy-test deploy-test-service \
        deploy-staging sync-dev-branches sync-lxd sync-all \
        check-lxd-git sync-dev-data

help:
	@echo ""
	@echo "  [인프라 전용] lxd/Makefile 명령어"
	@echo "  실행: make -f lxd/Makefile <target>"
	@echo ""
	@echo "  Docker Hub 배포:"
	@echo "    push                   모든 이미지 Docker Hub push"
	@echo "    push-local             로컬 레지스트리(10.10.10.10:5000) push"
	@echo "    deploy-test            빌드 → push → deploy-test 전체 배포"
	@echo "    deploy-test-service    단일 서비스 배포 (SVC=frontend|backend-api|ai-pipeline)"
	@echo ""
	@echo "  브랜치/LXD 싱크:"
	@echo "    sync-dev-branches      develop → dev/* 브랜치 병합 & push"
	@echo "    sync-lxd               각 LXD 서버에서 git pull 실행"
	@echo "    sync-all               위 두 작업 순차 실행"
	@echo ""
	@echo "  LXD 개발 환경:"
	@echo "    check-lxd-git          각 LXD 서버 git 설정(user/email/remote/SSH) 점검"
	@echo "    sync-dev-data          prod DB 콘텐츠 → 각 LXD 로컬 dev DB 동기화"
	@echo ""
	@echo "  변수:"
	@echo "    REGISTRY=$(REGISTRY)  TAG=$(TAG)"
	@echo ""

# --- Docker Hub Push ---
push:
	@echo "Docker Hub($(REGISTRY)) push..."
	docker push $(REGISTRY)/adelie-frontend:$(TAG)
	docker push $(REGISTRY)/adelie-backend-api:$(TAG)
	docker push $(REGISTRY)/adelie-ai-pipeline:$(TAG)

push-local:
	@for svc in frontend backend-api ai-pipeline; do \
		docker tag $(REGISTRY)/adelie-$$svc:$(TAG) 10.10.10.10:5000/adelie-$$svc:$(TAG); \
		docker push 10.10.10.10:5000/adelie-$$svc:$(TAG); \
	done

# --- Deploy-test (10.10.10.20) ---
deploy-test:
	$(MAKE) -C $(ROOT) build
	$(MAKE) push
	ssh deploy-test 'cd ~/adelie-investment && git pull origin develop && \
		docker compose -f docker-compose.prod.yml pull && \
		docker compose -f docker-compose.prod.yml up -d --remove-orphans && \
		docker exec adelie-frontend nginx -s reload 2>/dev/null || true'

deploy-test-service:
	$(MAKE) -C $(ROOT) build-$(SVC)
	docker push $(REGISTRY)/adelie-$(SVC):$(TAG)
	ssh deploy-test 'cd ~/adelie-investment && git pull origin develop && \
		docker compose -f docker-compose.prod.yml pull $(SVC) && \
		docker compose -f docker-compose.prod.yml up -d $(SVC) && \
		docker exec adelie-frontend nginx -s reload 2>/dev/null || true'

# --- 브랜치 싱크 (현재 git 계정 사용 — git config 강제 변경 없음) ---
sync-dev-branches:
	@echo "develop → dev/* 브랜치 싱크..."
	@cd $(ROOT) && CURRENT=$$(git branch --show-current); \
	for BRANCH in dev/frontend dev/backend dev/chatbot dev/pipeline dev/infra; do \
		echo "  -> $$BRANCH"; \
		git checkout $$BRANCH 2>/dev/null || { echo "  브랜치 없음, 건너뜀: $$BRANCH"; continue; }; \
		git merge develop --no-edit 2>/dev/null || true; \
		git push origin $$BRANCH; \
	done; \
	git checkout $$CURRENT
	@echo "완료: 모든 dev/* 브랜치 싱크"

# --- LXD 서버 코드 싱크 (lxc 명령 — 호스트에서만 동작) ---
sync-lxd:
	@echo "LXD 서버 코드 싱크..."
	lxc exec dev-yj99son  -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/frontend"
	lxc exec dev-j2hoon10 -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/chatbot"
	lxc exec dev-ryejinn  -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/pipeline"
	lxc exec dev-jjjh02   -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/backend"
	lxc exec dev-hj       -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/infra"
	@echo "완료: 모든 LXD 서버 코드 싱크"

# --- Staging (10.10.10.21) ---
deploy-staging:
	ssh staging 'cd ~/adelie-investment && git pull origin develop && \
		docker compose -f docker-compose.staging.yml pull && \
		docker compose -f docker-compose.staging.yml up -d --remove-orphans'
	@echo "✅ staging(10.10.10.21) 배포 완료"

sync-all: sync-dev-branches sync-lxd
	@echo "전체 싱크 완료 (브랜치 + LXD 서버)"

# --- LXD 서버 git 설정 점검 ---
check-lxd-git:
	@echo "=== LXD 서버 git 설정 점검 ==="
	@for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo ""; \
		echo "### $$srv ###"; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment 2>/dev/null || { echo '  ❌ 프로젝트 디렉토리 없음'; exit 0; }; \
			REMOTE=\$$(git remote get-url origin 2>/dev/null | sed 's|https://[^@]*@|https://***@|g' || echo '미설정'); \
			NAME=\$$(git config user.name 2>/dev/null || echo '❌ 미설정'); \
			EMAIL=\$$(git config user.email 2>/dev/null || echo '❌ 미설정'); \
			SSH_RESULT=\$$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -T git@github.com 2>&1 | grep -v '^Warning:' | head -1 || true); \
			[ -z \"\$$SSH_RESULT\" ] && SSH_RESULT='❌ SSH 미인증 (공개키 GitHub 미등록)'; \
			echo \"  remote : \$$REMOTE\"; \
			echo \"  user   : \$$NAME <\$$EMAIL>\"; \
			echo \"  ssh    : \$$SSH_RESULT\"; \
		" 2>/dev/null || echo "  ❌ LXC 연결 실패"; \
	done
	@echo ""
	@echo "=== 점검 완료 ==="

# --- prod DB 콘텐츠 → 각 LXD 로컬 dev DB 동기화 ---
# HOST(dev-hj)에서 실행: deploy-test prod 덤프 → 각 LXD 서버 로컬 postgres에 적용
sync-dev-data:
	@echo "=== deploy-test → 각 LXD 로컬 dev DB 콘텐츠 동기화 ==="
	@bash $(ROOT)/database/scripts/sync_dev_data.sh
	@echo "=== 동기화 완료 ==="
