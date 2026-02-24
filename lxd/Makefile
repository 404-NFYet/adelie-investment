# ============================================================
# lxd/Makefile — 인프라 전용 (dorae222/hj 서버에서만 실행)
# 사용법: make -f lxd/Makefile <target>
# ============================================================

ROOT := $(realpath $(dir $(lastword $(MAKEFILE_LIST)))..)
REGISTRY ?= dorae222
TAG ?= latest

.PHONY: help push push-local deploy-test deploy-test-service rollback-stable \
        sync-dev-branches sync-lxd sync-all \
        check-lxd-git sync-dev-data health-lxd fix-lxd-jwt \
        dev-final-branches dev-final-checkout dev-final-rebuild dev-final-setup \
        dev-local-db-setup

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
	@echo "    rollback-stable        feb20-stable 이미지로 deploy-test 롤백"
	@echo "  브랜치/LXD 싱크:"
	@echo "    sync-dev-branches      develop → dev/* 브랜치 병합 & push"
	@echo "    sync-lxd               각 LXD 서버에서 git pull 실행"
	@echo "    sync-all               위 두 작업 순차 실행"
	@echo ""
	@echo "  LXD 개발 환경:"
	@echo "    check-lxd-git          각 LXD 서버 git 설정(user/email/remote/SSH) 점검"
	@echo "    health-lxd             5대 서버 git 브랜치/Docker 컨테이너 상태 한눈에 보기"
	@echo "    fix-lxd-jwt            JWT_SECRET 기본값인 서버 자동 갱신 + backend-api 재시작"
	@echo "    sync-dev-data          prod DB 콘텐츠 → 각 LXD 로컬 dev DB 동기화"
	@echo ""
	@echo "  dev-final 워크플로우:"
	@echo "    dev-final-branches     release/feb20-stable + dev/* 머지 → dev-final/* 브랜치 생성 & push"
	@echo "    dev-final-checkout     각 LXD 서버에서 dev-final/* 브랜치 checkout"
	@echo "    dev-final-rebuild      각 LXD 서버 Docker 재빌드 + up -d"
	@echo "    dev-final-setup        위 3단계 순차 실행 (전체 셋업)"
	@echo ""
	@echo "  개인 로컬 DB 초기화:"
	@echo "    dev-local-db-setup     postgres 기동 + alembic upgrade + prod 데이터 복제 + backend-api 재시작"
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

## feb20-stable 이미지로 deploy-test 빠른 롤백
rollback-stable:
	@echo "=== 롤백: feb20-stable → deploy-test ==="
	ssh deploy-test ' \
	  cd ~/adelie-investment && \
	  git fetch origin && \
	  git checkout release/feb20-stable && \
	  docker pull dorae222/adelie-frontend:feb20-stable && \
	  docker pull dorae222/adelie-backend-api:feb20-stable && \
	  TAG=feb20-stable docker compose -f docker-compose.prod.yml up -d --no-deps frontend backend-api && \
	  docker exec adelie-frontend nginx -s reload 2>/dev/null || true && \
	  echo "✅ 롤백 완료:" && docker ps --format "{{.Names}}: {{.Image}}" | grep -E "frontend|backend-api" \
	'
	@echo "=== rollback-stable 완료 ==="

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
# git pull 후 frontend dev 이미지 빌드 및 up -d 포함
sync-lxd:
	@echo "LXD 서버 코드 싱크 (git pull → frontend build → up -d)..."
	@lxc exec dev-yj99son  -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/frontend && \
		docker compose -f docker-compose.dev.yml build frontend 2>&1 | tail -3 && \
		docker compose -f docker-compose.dev.yml up -d frontend" && echo "  ✅ dev-yj99son" || echo "  ❌ dev-yj99son"
	@lxc exec dev-j2hoon10 -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/chatbot && \
		docker compose -f docker-compose.dev.yml build frontend 2>&1 | tail -3 && \
		docker compose -f docker-compose.dev.yml up -d frontend" && echo "  ✅ dev-j2hoon10" || echo "  ❌ dev-j2hoon10"
	@lxc exec dev-ryejinn  -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/pipeline && \
		docker compose -f docker-compose.dev.yml build frontend 2>&1 | tail -3 && \
		docker compose -f docker-compose.dev.yml up -d frontend" && echo "  ✅ dev-ryejinn" || echo "  ❌ dev-ryejinn"
	@lxc exec dev-jjjh02   -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/backend && \
		docker compose -f docker-compose.dev.yml build frontend 2>&1 | tail -3 && \
		docker compose -f docker-compose.dev.yml up -d frontend" && echo "  ✅ dev-jjjh02" || echo "  ❌ dev-jjjh02"
	@lxc exec dev-hj       -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/infra && \
		docker compose -f docker-compose.dev.yml build frontend 2>&1 | tail -3 && \
		docker compose -f docker-compose.dev.yml up -d frontend" && echo "  ✅ dev-hj" || echo "  ❌ dev-hj"
	@echo "완료: 모든 LXD 서버 코드 싱크"

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

# --- LXD 5대 서버 헬스체크 (git 브랜치 + Docker 컨테이너 상태) ---
health-lxd:
	@echo "=== LXD 서버 헬스체크 ==="
	@for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo ""; \
		echo "### $$srv ###"; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment 2>/dev/null || { echo '  ❌ 프로젝트 디렉토리 없음'; exit 0; }; \
			BRANCH=\$$(git branch --show-current 2>/dev/null || echo '❓ 미확인'); \
			AHEAD=\$$(git rev-list @{u}..HEAD 2>/dev/null | wc -l || echo '?'); \
			BEHIND=\$$(git rev-list HEAD..@{u} 2>/dev/null | wc -l || echo '?'); \
			echo \"  브랜치  : \$$BRANCH (↑\$$AHEAD ↓\$$BEHIND)\"; \
			echo '  컨테이너:'; \
			docker compose -f docker-compose.dev.yml ps --format 'table {{.Name}}\t{{.Status}}' 2>/dev/null | tail -n +2 | \
				awk '{printf \"    %-35s %s\n\", \$$1, \$$2}'; \
		" 2>/dev/null || echo "  ❌ LXC 연결 실패"; \
	done
	@echo ""
	@echo "=== 헬스체크 완료 ==="

# --- JWT_SECRET 기본값 서버 자동 수정 ---
# .env의 JWT_SECRET이 기본값이면 새 랜덤값으로 교체 후 backend-api 재시작
fix-lxd-jwt:
	@echo "=== JWT_SECRET 기본값 서버 수정 ==="
	@DEFAULT_JWT="narrative-invest-jwt-secret-change-in-production"; \
	for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo ""; \
		echo "### $$srv ###"; \
		lxc exec $$srv -- bash -c " \
			ENV_FILE=\$$(ls /home/ubuntu/adelie-investment/.env 2>/dev/null | head -1); \
			[ -z \"\$$ENV_FILE\" ] && { echo '  ❌ .env 파일 없음'; exit 0; }; \
			DIR=\$$(dirname \$$ENV_FILE); \
			CURRENT_JWT=\$$(grep '^JWT_SECRET=' \$$ENV_FILE | cut -d= -f2-); \
			if [ \"\$$CURRENT_JWT\" = 'narrative-invest-jwt-secret-change-in-production' ]; then \
				NEW_JWT=\$$(openssl rand -hex 32); \
				sed -i \"s|JWT_SECRET=.*|JWT_SECRET=\$$NEW_JWT|\" \$$ENV_FILE; \
				echo '  🔧 JWT_SECRET 갱신 완료'; \
				cd \$$DIR && docker compose -f docker-compose.dev.yml restart backend-api 2>&1 | tail -2; \
				sleep 8; \
				STATUS=\$$(docker compose -f docker-compose.dev.yml ps backend-api --format '{{.Status}}' 2>/dev/null); \
				echo \"  상태: \$$STATUS\"; \
			else \
				echo '  ✅ JWT_SECRET 정상 (기본값 아님)'; \
			fi; \
		" 2>/dev/null || echo "  ❌ LXC 연결 실패"; \
	done
	@echo ""
	@echo "=== JWT 수정 완료 ==="

# --- dev-final/* 브랜치 워크플로우 ---

# Step 1: dev-final/* 브랜치 생성 (release/feb20-stable + dev/* 머지)
dev-final-branches:
	@echo "=== dev-final/* 브랜치 생성 (feb20-stable + dev/* 머지) ==="
	@cd $(ROOT) && CURRENT=$$(git branch --show-current); \
	git fetch origin; \
	for entry in "frontend:dev/frontend" "chatbot:dev/chatbot" "backend:dev/backend" "pipeline:dev/pipeline" "infra:dev/infra"; do \
		part=$${entry%%:*}; src=$${entry##*:}; \
		echo ""; \
		echo "  → dev-final/$$part (← origin/$$src)"; \
		git checkout release/feb20-stable 2>/dev/null || { echo "  ❌ release/feb20-stable 없음"; continue; }; \
		git checkout -b dev-final/$$part 2>/dev/null || git checkout dev-final/$$part; \
		if git merge --no-edit origin/$$src 2>/dev/null; then \
			git push origin dev-final/$$part \
				&& echo "  ✅ dev-final/$$part push 완료" \
				|| echo "  ⚠️  push 실패 — 권한 또는 remote 확인"; \
		else \
			echo "  ⚠️  dev-final/$$part: 충돌 발생 — 수동 해결 후 git push origin dev-final/$$part 실행"; \
			git merge --abort 2>/dev/null || true; \
		fi; \
	done; \
	git checkout $$CURRENT
	@echo ""
	@echo "=== 브랜치 생성 완료 ==="

# Step 2: 각 LXD 서버에서 dev-final/* checkout
dev-final-checkout:
	@echo "=== 각 LXD 서버 dev-final/* checkout ==="
	@lxc exec dev-yj99son  -- bash -c "cd /home/ubuntu/adelie-investment && git fetch origin && git stash 2>/dev/null || true && git checkout dev-final/frontend  && echo '  ✅ dev-yj99son: dev-final/frontend'"  2>/dev/null && true || echo "  ❌ dev-yj99son"
	@lxc exec dev-j2hoon10 -- bash -c "cd /home/ubuntu/adelie-investment && git fetch origin && git stash 2>/dev/null || true && git checkout dev-final/chatbot   && echo '  ✅ dev-j2hoon10: dev-final/chatbot'"  2>/dev/null && true || echo "  ❌ dev-j2hoon10"
	@lxc exec dev-jjjh02   -- bash -c "cd /home/ubuntu/adelie-investment && git fetch origin && git stash 2>/dev/null || true && git checkout dev-final/backend   && echo '  ✅ dev-jjjh02: dev-final/backend'"   2>/dev/null && true || echo "  ❌ dev-jjjh02"
	@lxc exec dev-ryejinn  -- bash -c "cd /home/ubuntu/adelie-investment && git fetch origin && git stash 2>/dev/null || true && git checkout dev-final/pipeline  && echo '  ✅ dev-ryejinn: dev-final/pipeline'"  2>/dev/null && true || echo "  ❌ dev-ryejinn"
	@lxc exec dev-hj       -- bash -c "cd /home/ubuntu/adelie-investment && git fetch origin && git stash 2>/dev/null || true && git checkout dev-final/infra     && echo '  ✅ dev-hj: dev-final/infra'"        2>/dev/null && true || echo "  ❌ dev-hj"
	@echo "=== checkout 완료 (미커밋 변경사항은 각 서버 git stash list 확인) ==="

# Step 3: 각 LXD 서버 Docker 재빌드 + up -d (frontend + backend-api만, ai-pipeline 제외)
dev-final-rebuild:
	@echo "=== 각 LXD 서버 Docker 재빌드 (frontend + backend-api) ==="
	@for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo ""; \
		echo "  📦 $$srv 빌드 중..."; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment && \
			docker compose -f docker-compose.dev.yml build frontend backend-api 2>&1 | tail -3 && \
			docker compose -f docker-compose.dev.yml up -d --remove-orphans" \
			&& echo "  ✅ $$srv 재시작 완료" || echo "  ❌ $$srv 빌드 실패"; \
	done
	@echo ""
	@echo "=== 재빌드 완료 (ai-pipeline은 필요 시 수동: docker compose build ai-pipeline) ==="

# dev-final 전체 셋업 (브랜치 생성 → checkout → 재빌드)
dev-final-setup: dev-final-branches dev-final-checkout dev-final-rebuild
	@echo ""
	@echo "✅ dev-final 전체 셋업 완료"
	@echo "   다음 단계: 파이프라인 수집 완료 후 → make -f lxd/Makefile sync-dev-data"

# --- 팀원별 개인 로컬 DB 초기화 + prod 데이터 복제 ---
# HOST(dev-hj)에서 실행: postgres 기동 → alembic upgrade → prod 덤프 → 각 서버 로컬 DB 적용
dev-local-db-setup:
	@echo "=== Step 1: 로컬 postgres/redis 기동 + alembic upgrade head ==="
	@for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo "  → $$srv..."; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment && \
			docker compose -f docker-compose.dev.yml up -d postgres redis && sleep 6 && \
			docker compose -f docker-compose.dev.yml run --rm backend-api \
				sh -c 'cd /app/database && alembic upgrade heads 2>&1 | tail -3'" \
			&& echo "  ✅ $$srv" || echo "  ❌ $$srv"; \
	done
	@echo ""
	@echo "=== Step 2: deploy-test → 각 서버 로컬 DB 데이터 복제 ==="
	@DUMP=/tmp/adelie_prod_$$(date +%Y%m%d%H%M).sql; \
	echo "  prod 덤프 생성 중..."; \
	ssh deploy-test "docker exec adelie-postgres pg_dump \
		-U narative -d narrative_invest --data-only --disable-triggers \
		-t stock_listings -t daily_briefings -t briefing_stocks \
		-t historical_cases -t case_matches -t case_stock_relations \
		-t broker_reports" > $$DUMP; \
	echo "  덤프 완료: $$DUMP ($$(wc -c < $$DUMP) bytes)"; \
	for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo "  → $$srv 복제 중..."; \
		lxc exec $$srv -- bash -c " \
			docker exec -i adelie-investment-postgres-1 \
				psql -U narative -d narrative_invest" < $$DUMP \
			&& echo "  ✅ $$srv" || echo "  ❌ $$srv"; \
	done; \
	rm -f $$DUMP
	@echo ""
	@echo "=== Step 3: backend-api 재시작 ==="
	@for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment && \
			docker compose -f docker-compose.dev.yml restart backend-api 2>&1 | tail -1" \
			&& echo "  ✅ $$srv" || echo "  ❌ $$srv"; \
	done
	@echo ""
	@echo "✅ dev-local-db-setup 완료"
	@echo "   각 서버 API: http://<서버IP>:8082/api/v1/health"
