# ============================================================
# lxd/Makefile — 인프라 전용 (dorae222/hj 서버에서만 실행)
# 사용법: make -f lxd/Makefile help
# ============================================================

ROOT     := $(realpath $(dir $(lastword $(MAKEFILE_LIST)))..)
REGISTRY ?= dorae222
TAG      ?= latest

.PHONY: help \
        health git-check jwt-fix sync db-sync \
        push push-local deploy rollback \
        dev-final-setup dev-final-sync dev-final-branches dev-final-checkout dev-final-rebuild \
        db-local-setup \
        health-lxd check-lxd-git fix-lxd-jwt sync-lxd sync-dev-data sync-dev-branches sync-all \
        dev-local-db-setup

# ============================================================
# 도움말
# ============================================================
help:
	@echo ""
	@echo "  [인프라 전용] lxd/Makefile — make -f lxd/Makefile <target>"
	@echo "  ============================================================"
	@echo ""
	@echo "  [LXD 서버 관리]"
	@echo "    health           5대 서버 브랜치 + Docker 컨테이너 상태 한눈에 보기"
	@echo "    git-check        각 서버 git user/email/remote 설정 점검"
	@echo "    jwt-fix          JWT_SECRET 기본값 서버 자동 갱신 + backend-api 재시작"
	@echo "    sync             각 서버 git pull + docker compose up -d"
	@echo "    db-sync          prod DB 콘텐츠 → 각 서버 로컬 dev DB 복제"
	@echo ""
	@echo "  [Docker Hub 배포]"
	@echo "    push             이미지 빌드 + Docker Hub push (TAG=$(TAG))"
	@echo "    deploy           deploy-test 배포 (빌드 → push → SSH pull + up -d)"
	@echo "    rollback         feb20-stable 이미지로 deploy-test 롤백"
	@echo ""
	@echo "  [dev-final 환경]"
	@echo "    dev-final-setup  브랜치 생성 + LXD checkout + 재빌드 (전체)"
	@echo "    dev-final-sync   각 서버 dev-final/* pull + up -d"
	@echo "    db-local-setup   로컬 postgres 기동 + alembic + prod 데이터 복제"
	@echo ""
	@echo "  변수: REGISTRY=$(REGISTRY)  TAG=$(TAG)"
	@echo ""

# ============================================================
# LXD 서버 관리
# ============================================================

# 5대 서버 브랜치/Docker 상태 한눈에 보기
health:
	@echo "=== LXD 서버 헬스체크 ==="
	@for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo ""; \
		echo "### $$srv ###"; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment 2>/dev/null || { echo '  ❌ 프로젝트 디렉토리 없음'; exit 0; }; \
			BRANCH=\$$(git branch --show-current 2>/dev/null || echo '❓'); \
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

# 각 서버 git user/email/remote 설정 점검
git-check:
	@echo "=== LXD 서버 git 설정 점검 ==="
	@for srv in dev-yj99son dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-hj; do \
		echo ""; \
		echo "### $$srv ###"; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment 2>/dev/null || { echo '  ❌ 프로젝트 디렉토리 없음'; exit 0; }; \
			REMOTE=\$$(git remote get-url origin 2>/dev/null | sed 's|https://[^@]*@|https://***@|g' || echo '미설정'); \
			NAME=\$$(git config user.name 2>/dev/null || echo '❌ 미설정'); \
			EMAIL=\$$(git config user.email 2>/dev/null || echo '❌ 미설정'); \
			echo \"  remote : \$$REMOTE\"; \
			echo \"  user   : \$$NAME <\$$EMAIL>\"; \
		" 2>/dev/null || echo "  ❌ LXC 연결 실패"; \
	done
	@echo ""
	@echo "=== 점검 완료 ==="

# JWT_SECRET 기본값 서버 자동 갱신
jwt-fix:
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
				echo '  JWT_SECRET 갱신 완료'; \
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

# 각 서버 git pull + docker compose up -d
# (dev-final/* 브랜치 기준 — 각 서버가 해당 브랜치를 체크아웃한 상태)
sync:
	@echo "=== LXD 서버 코드 싱크 (git pull → up -d) ==="
	@for entry in \
		"dev-yj99son:dev-final/frontend" \
		"dev-j2hoon10:dev-final/chatbot" \
		"dev-jjjh02:dev-final/backend" \
		"dev-ryejinn:dev-final/pipeline" \
		"dev-hj:dev-final/infra"; \
	do \
		srv=$${entry%%:*}; branch=$${entry##*:}; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment && \
			git pull origin $$branch && \
			docker compose -f docker-compose.dev.yml build frontend 2>&1 | tail -2 && \
			docker compose -f docker-compose.dev.yml up -d" \
			&& echo "  ✅ $$srv" || echo "  ❌ $$srv"; \
	done
	@echo "=== 싱크 완료 ==="

# prod DB 콘텐츠 → 각 서버 로컬 dev DB 복제
db-sync:
	@echo "=== deploy-test → 각 LXD 로컬 dev DB 콘텐츠 동기화 ==="
	@bash $(ROOT)/database/scripts/sync_dev_data.sh
	@echo "=== 동기화 완료 ==="

# ============================================================
# Docker Hub 배포
# ============================================================

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

deploy:
	$(MAKE) -C $(ROOT) build
	$(MAKE) push
	ssh deploy-test 'cd ~/adelie-investment && git pull origin develop && \
		docker compose -f docker-compose.prod.yml pull && \
		docker compose -f docker-compose.prod.yml up -d --remove-orphans && \
		docker exec adelie-frontend nginx -s reload 2>/dev/null || true'

deploy-service:
	$(MAKE) -C $(ROOT) build-$(SVC)
	docker push $(REGISTRY)/adelie-$(SVC):$(TAG)
	ssh deploy-test 'cd ~/adelie-investment && git pull origin develop && \
		docker compose -f docker-compose.prod.yml pull $(SVC) && \
		docker compose -f docker-compose.prod.yml up -d $(SVC) && \
		docker exec adelie-frontend nginx -s reload 2>/dev/null || true'

rollback:
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
	@echo "=== rollback 완료 ==="

# ============================================================
# dev-final 환경
# ============================================================

# 전체 셋업 (브랜치 생성 → checkout → 재빌드)
dev-final-setup: dev-final-branches dev-final-checkout dev-final-rebuild
	@echo ""
	@echo "✅ dev-final 전체 셋업 완료"
	@echo "   다음 단계: 파이프라인 수집 완료 후 → make -f lxd/Makefile db-sync"

# 각 서버 dev-final/* pull + up -d
dev-final-sync:
	@echo "=== dev-final/* 코드 싱크 (pull + up -d) ==="
	@for entry in \
		"dev-yj99son:dev-final/frontend" \
		"dev-j2hoon10:dev-final/chatbot" \
		"dev-jjjh02:dev-final/backend" \
		"dev-ryejinn:dev-final/pipeline" \
		"dev-hj:dev-final/infra"; \
	do \
		srv=$${entry%%:*}; branch=$${entry##*:}; \
		lxc exec $$srv -- bash -c " \
			cd /home/ubuntu/adelie-investment && \
			git pull origin $$branch && \
			docker compose -f docker-compose.dev.yml up -d --remove-orphans" \
			&& echo "  ✅ $$srv ($$branch)" || echo "  ❌ $$srv"; \
	done
	@echo "=== dev-final 싱크 완료 ==="

# Step 1: dev-final/* 브랜치 생성 (develop 기준)
dev-final-branches:
	@echo "=== dev-final/* 브랜치 생성 (develop 기준) ==="
	@cd $(ROOT) && CURRENT=$$(git branch --show-current); \
	git fetch origin; \
	for part in frontend chatbot backend pipeline infra; do \
		echo ""; \
		echo "  → dev-final/$$part"; \
		git checkout develop 2>/dev/null; \
		git checkout -b dev-final/$$part 2>/dev/null || git checkout dev-final/$$part; \
		git push origin dev-final/$$part \
			&& echo "  ✅ dev-final/$$part push 완료" \
			|| echo "  ⚠️  push 실패 — 권한 또는 remote 확인"; \
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
	@echo "=== checkout 완료 (미커밋 변경사항 → git stash list 확인) ==="

# Step 3: 각 LXD 서버 Docker 재빌드 + up -d
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
	@echo "=== 재빌드 완료 ==="

# 팀원별 개인 로컬 DB 초기화 + prod 데이터 복제
db-local-setup:
	@echo "=== Step 1: 로컬 postgres/redis 기동 + alembic upgrade heads ==="
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
	@echo "✅ db-local-setup 완료"
	@echo "   각 서버 API: http://<서버IP>:8082/api/v1/health"

# ============================================================
# 하위 호환 별칭 (구 타겟명 → 새 타겟명)
# ============================================================
health-lxd:        health
check-lxd-git:     git-check
fix-lxd-jwt:       jwt-fix
sync-lxd:          sync
sync-dev-data:     db-sync
sync-dev-branches: dev-final-branches
sync-all:          sync
dev-local-db-setup: db-local-setup
deploy-test:       deploy
rollback-stable:   rollback
deploy-test-service: deploy-service
