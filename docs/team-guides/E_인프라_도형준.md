# 인프라 개발 가이드 — 도형준

## 환경 정보
- LXD 컨테이너: `ssh dev-hj`
- Git 설정: user.name=dorae222, user.email=dhj9842@gmail.com
- 브랜치: `dev/infra`

## 개발 시작

### Docker Compose 환경
```bash
# 개발 환경
make dev                         # frontend + backend-api + postgres + redis
make dev-frontend                # frontend만
make dev-api                     # backend-api만

# 테스트 환경
make test                        # backend unit tests
make test-e2e                    # Playwright E2E tests

# 프로덕션 환경 (로컬 검증)
make build                       # 모든 이미지 빌드
docker compose -f docker-compose.prod.yml up -d
```

### deploy-test 원격 배포
```bash
# 1단계: 이미지 빌드 + Docker Hub 푸시
make build && make push

# 2단계: 원격 서버 배포
make deploy
# 또는 수동
ssh deploy-test 'cd ~/adelie-investment && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d'
```

## 담당 디렉토리

```
adelie-investment/
├── docker-compose.dev.yml       # 개발 환경 (HMR, auto-reload)
├── docker-compose.test.yml      # 테스트 환경 (pytest)
├── docker-compose.prod.yml      # 프로덕션 환경
├── Makefile                     # 빌드/배포 명령 단축키
├── .env.example                 # 환경변수 템플릿
├── fastapi/
│   ├── Dockerfile               # Backend API 이미지
│   └── requirements.txt
├── datapipeline/
│   ├── Dockerfile               # Pipeline 이미지
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile.dev           # 개발용 (Vite)
│   ├── Dockerfile.prod          # 프로덕션용 (nginx)
│   ├── nginx.conf               # nginx 설정 (/api/v1/* 프록시)
│   └── package.json
├── database/
│   ├── alembic/                 # DB 마이그레이션
│   ├── alembic.ini
│   └── scripts/                 # DB 관리 스크립트
│       ├── create_database.py
│       ├── reset_db.py
│       └── init_stock_listings.py
├── lxd/                         # LXD 컨테이너 설정
│   ├── init-dev-container.sh    # 개발 컨테이너 생성 스크립트
│   └── setup-git-worktree.sh    # git worktree 초기화
└── tests/
    ├── e2e/                     # Playwright E2E
    └── load/                    # Locust 부하 테스트
```

### 핵심 파일
- `Makefile`: 빌드/배포/테스트 명령 정의
- `docker-compose.*.yml`: 서비스 정의, 네트워크, 볼륨
- `fastapi/Dockerfile`: multi-stage build (chatbot, datapipeline 포함)
- `frontend/nginx.conf`: SPA 라우팅 + API 프록시
- `database/alembic/env.py`: 비동기 마이그레이션 설정

## 개발 워크플로우

### 1. Docker 이미지 빌드
```bash
# 전체 빌드
make build

# 개별 빌드
make build-frontend
make build-api
docker build -t dorae222/adelie-pipeline:latest -f datapipeline/Dockerfile .
```

### 2. Docker Hub 푸시
```bash
make push
# 또는
docker push dorae222/adelie-frontend:latest
docker push dorae222/adelie-backend-api:latest
docker push dorae222/adelie-pipeline:latest
```

### 3. 배포 (deploy-test)
```bash
# 전체 배포
make deploy

# 수동 배포
ssh deploy-test
cd ~/adelie-investment  # 주의: ~/adelie가 아님!
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# 특정 서비스만 재시작
docker compose -f docker-compose.prod.yml restart backend-api
```

### 4. DB 마이그레이션
```bash
# 로컬 (가상환경)
cd database
../.venv/bin/alembic upgrade head

# Docker (개발)
docker compose -f docker-compose.dev.yml run db-migrate

# Docker (프로덕션, 로컬 검증)
docker compose -f docker-compose.prod.yml exec backend-api sh -c "cd /app/database && alembic upgrade head"

# deploy-test (원격)
ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'
```

### 5. 로그 확인
```bash
# 로컬
docker compose -f docker-compose.dev.yml logs -f backend-api
docker compose -f docker-compose.dev.yml logs -f frontend

# deploy-test
ssh deploy-test 'docker logs -f adelie-backend-api'
ssh deploy-test 'docker logs -f adelie-frontend'
```

## 테스트

### Unit 테스트 (Backend)
```bash
make test
# 또는
docker compose -f docker-compose.test.yml run --rm backend-test
```

### E2E 테스트 (Playwright)
```bash
make test-e2e
# 또는
cd tests/e2e
npx playwright test
```

### 부하 테스트 (Locust)
```bash
make test-load
# 또는
cd tests/load
locust -f locustfile.py --headless -u 40 -r 10 -t 5m
```

## 다른 파트와의 연동

### Backend (허진서)
- **영향받는 경우**:
  - 새 환경변수 추가 → `docker-compose.*.yml`, `.env.example` 업데이트
  - DB 마이그레이션 → 배포 전 실행 확인
  - requirements.txt 변경 → 이미지 재빌드
- **협업 필요**:
  - Alembic migration 파일 공유 → 배포 순서 조율
  - FastAPI 의존성 추가 → Dockerfile 최적화 검토
- **주의**:
  - 마이그레이션 실패 시 롤백 계획
  - Docker 이미지 빌드 시간 (약 5~10분)

### Frontend (손영진)
- **영향받는 경우**:
  - nginx.conf 변경 → 이미지 재빌드
  - 환경변수 추가 → `docker-compose.*.yml` 업데이트
  - package.json 변경 → 이미지 재빌드
- **협업 필요**:
  - 프로덕션 빌드 검증 → `make build-frontend` 테스트
  - API 프록시 경로 변경 시 nginx.conf 수정
- **주의**:
  - SPA 라우팅 (모든 경로 → index.html)
  - nginx 캐싱 설정 (static assets)

### Chatbot (정지훈)
- **영향받는 경우**:
  - chatbot 모듈 변경 → backend-api 이미지 재빌드
  - 새 LangChain 의존성 → fastapi/requirements.txt 업데이트
- **협업 필요**:
  - LangSmith API 키 → `.env` 환경변수 추가
  - SSE 성능 문제 → nginx timeout 설정 조정
- **주의**: chatbot은 backend-api 이미지에 포함 (별도 서비스 아님)

### Pipeline (안례진)
- **영향받는 경우**:
  - datapipeline 모듈 변경 → pipeline 이미지 재빌드
  - 새 API 키 → `.env` 환경변수 추가
  - 스케줄링 설정 → cron 또는 docker-compose 설정
- **협업 필요**:
  - Live 모드 실행 시간 고려 (약 10~20분)
  - DB 저장 실패 시 알림 메커니즘
- **주의**:
  - pipeline은 `--profile pipeline`로 분리 (기본 실행 안 됨)
  - 프로덕션에서 cron 또는 수동 실행

## 환경변수 관리

### .env 파일 구조
```bash
# 로컬 개발 (.env)
DATABASE_URL=postgresql+asyncpg://narative:password@localhost:5433/narrative_invest
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=lsv2_...

# deploy-test (.env)
DATABASE_URL=postgresql+asyncpg://narative:password@postgres:5432/narrative_invest
REDIS_URL=redis://redis:6379/0
```

### docker-compose에서 환경변수 전달
```yaml
services:
  backend-api:
    env_file:
      - .env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

## 롤백 가이드

### 이미지 롤백
```bash
# 1. 이전 이미지 태그 확인
docker images dorae222/adelie-backend-api

# 2. docker-compose.prod.yml에서 이미지 태그 변경
# image: dorae222/adelie-backend-api:latest
# → image: dorae222/adelie-backend-api:previous-tag

# 3. 재배포
ssh deploy-test 'cd ~/adelie-investment && docker compose -f docker-compose.prod.yml up -d backend-api'
```

### DB 마이그레이션 롤백
```bash
# 로컬
cd database
../.venv/bin/alembic downgrade -1

# deploy-test
ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic downgrade -1"'
```

## LXD 컨테이너 관리

### 새 개발자 컨테이너 생성
```bash
# 호스트 서버 (10.10.10.20)
cd /home/ubuntu/adelie-investment/lxd
./init-dev-container.sh dev-newname

# 컨테이너 접속
lxc exec dev-newname -- su - ubuntu
```

### git worktree 초기화
```bash
# 컨테이너 내부
cd ~/adelie-investment
./lxd/setup-git-worktree.sh dev/feature-branch
```

## LXD 개발환경 운영 (2026-02-22 이후)

### lxd/Makefile 타겟 요약

```bash
# 5대 서버 전체 헬스체크 (브랜치 + 컨테이너 상태)
make -f lxd/Makefile health-lxd

# JWT_SECRET 기본값 서버 자동 수정 + backend-api 재시작
make -f lxd/Makefile fix-lxd-jwt

# git pull → frontend 빌드 → up -d (원스텝 동기화)
make -f lxd/Makefile sync-lxd

# staging(10.10.10.21) 배포
make -f lxd/Makefile deploy-staging

# deploy-test 전체 배포
make -f lxd/Makefile deploy-test
```

### 자주 발생하는 LXD 이슈

| 증상 | 원인 | 해결 |
|------|------|------|
| backend-api UNHEALTHY | JWT_SECRET 기본값 | `make -f lxd/Makefile fix-lxd-jwt` |
| frontend pull 실패 | Docker Hub 미존재 | `make -f lxd/Makefile sync-lxd` (로컬 빌드) |
| git pull 충돌 | 로컬 커밋 존재 | `lxc exec dev-X -- bash -c "cd ~/adelie-investment && git stash && git pull"` |

### staging 서버 (10.10.10.21) 관리

```bash
# 연결 확인
ssh staging 'hostname && docker ps'

# develop 최신 배포
make -f lxd/Makefile deploy-staging

# 초기 설치 (신규 서버)
ssh staging 'git clone https://github.com/404-NFYet/adelie-investment.git ~/adelie-investment && cd ~/adelie-investment && git checkout develop'
scp deploy-test:~/adelie-investment/.env staging:~/adelie-investment/.env
ssh staging 'cd ~/adelie-investment && docker compose -f docker-compose.staging.yml up -d'
ssh staging 'docker exec staging-backend-api sh -c "cd /app/database && alembic upgrade head"'
```

## AWS Terraform IaC (2026-02-22 이후)

### 모듈 구조

```
infra/terraform/
├── variables.tf          # 루트 변수 (103라인)
├── outputs.tf            # 루트 출력 (36라인)
├── modules/
│   ├── network/          # VPC, 서브넷, IGW, 보안그룹
│   ├── compute/          # ECS Fargate, ECR, IAM
│   ├── database/         # RDS PostgreSQL
│   ├── storage/          # S3, ElastiCache Redis
│   └── cdn/              # CloudFront
└── environments/
    ├── staging/main.tf   # staging 환경 (10.10.10.21 → AWS 이전 후)
    └── prod/main.tf      # production 환경
```

### 배포 준비 (AWS 이전 Phase 5 예정)

```bash
# 초기화 (staging 환경)
cd infra/terraform/environments/staging
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply

# ECR 이미지 빌드/푸시 (GitHub Actions deploy-aws.yml 트리거)
gh workflow run deploy-aws.yml -f environment=staging
```

> ⚠️ AWS 이전은 Phase 5 일정 확정 후 진행. 현재는 기존 LXD + deploy-test 운영 유지.

## 커밋 전 체크리스트
- [ ] `git config user.name` = dorae222
- [ ] `git config user.email` = dhj9842@gmail.com
- [ ] docker-compose 변경 시 로컬 테스트 (`make dev`)
- [ ] Dockerfile 변경 시 이미지 빌드 성공 확인 (`make build`)
- [ ] 환경변수 추가 시 `.env.example` 업데이트
- [ ] 마이그레이션 추가 시 로컬 실행 확인
- [ ] deploy-test 배포 전 팀원 알림 (다운타임 발생 가능)
- [ ] 커밋 메시지 형식: `chore: Docker Compose 네트워크 설정 개선` (한글, type prefix)
