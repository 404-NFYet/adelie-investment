# 빠른 시작 가이드

Adelie Investment 개발 환경을 설정하고 실행하는 방법을 안내합니다.

## 1. LXD 컨테이너 접속

각 팀원은 개인 LXD 컨테이너에서 작업합니다.

```bash
# SSH 접속 (호스트 머신에서)
ssh dev-yj99son     # 손영진
ssh dev-j2hoon10    # 정지훈
ssh dev-ryejinn     # 안례진
ssh dev-jjjh02      # 허진서
ssh dev-hj          # 도형준

# 또는 IP 직접 접속
ssh ubuntu@10.10.10.XXX
```

## 2. Git 설정 확인

첫 접속 시 Git 사용자 정보를 확인하고 설정합니다.

```bash
# 현재 설정 확인
git config user.name
git config user.email

# 설정이 올바르지 않으면 수정
git config user.name "YJ99Son"          # 예시: 손영진
git config user.email "syjin2008@naver.com"
```

**팀원별 Git 계정**

| 이름 | user.name | user.email |
|------|-----------|------------|
| 손영진 | YJ99Son | syjin2008@naver.com |
| 정지훈 | J2hoon10 | myhome559755@naver.com |
| 안례진 | ryejinn | arj1018@ewhain.net |
| 허진서 | jjjh02 | jinnyshur0104@gmail.com |
| 도형준 | dorae222 | dhj9842@gmail.com |

## 3. 프로젝트 클론 및 환경 설정

```bash
# 프로젝트 루트로 이동 (이미 클론되어 있음)
cd ~/adelie-investment

# 최신 코드 가져오기
git pull origin develop

# .env 파일 확인 (없으면 생성)
cp .env.example .env
```

`.env` 파일에 필수 환경 변수를 설정합니다. (자세한 내용은 6번 항목 참조)

## 4. Docker로 전체 스택 실행

개발 환경은 Docker Compose로 실행합니다.

```bash
# 전체 스택 실행 (frontend + backend-api + postgres + redis)
docker compose -f docker-compose.dev.yml up -d

# 또는 Makefile 사용
make dev
```

**개별 서비스만 실행**

```bash
# 프론트엔드만
make dev-frontend

# 백엔드 API만
make dev-api

# 중지
make dev-down
```

**로컬 실행 (Docker 없이)**

```bash
# 프론트엔드 로컬 실행
cd frontend
npm install
npm run dev
# http://localhost:3001

# 백엔드 API 로컬 실행 (별도 터미널)
cd fastapi
source ../.venv/bin/activate  # 가상환경 활성화
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
# http://localhost:8082
```

## 5. 실행 확인 체크리스트

모든 서비스가 정상 실행되었는지 확인합니다.

```bash
# 컨테이너 상태 확인
docker compose -f docker-compose.dev.yml ps

# 각 서비스 포트 확인
netstat -tuln | grep -E '(5433|6379|8082|3001)'
```

**확인 항목**

- [ ] PostgreSQL: `localhost:5433` (컨테이너 이름: `dev-postgres`)
- [ ] Redis: `localhost:6379` (컨테이너 이름: `dev-redis`)
- [ ] Backend API: `http://localhost:8082` (컨테이너 이름: `dev-backend-api`)
- [ ] Frontend: `http://localhost:3001` (컨테이너 이름: `dev-frontend`)

**브라우저 테스트**

```bash
# 백엔드 헬스체크
curl http://localhost:8082/health

# 프론트엔드 접속
curl http://localhost:3001
```

프론트엔드는 웹 브라우저에서 `http://localhost:3001`로 접속합니다.

## 6. 환경 변수 설정 (.env)

`.env` 파일에 다음 필수 변수를 설정해야 합니다.

```bash
# AI API 키 (필수)
OPENAI_API_KEY=sk-proj-...
PERPLEXITY_API_KEY=pplx-...
LANGCHAIN_API_KEY=lsv2_pt_...

# 선택 (Writer 에이전트용)
CLAUDE_API_KEY=sk-ant-...

# Database (기본값 사용 가능)
DATABASE_URL=postgresql+asyncpg://narative:password@localhost:5433/narrative_invest

# Redis (기본값 사용 가능)
REDIS_URL=redis://localhost:6379

# MinIO (프로덕션 환경에서 필요)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

**환경 변수 확인**

```bash
# .env 파일이 제대로 로드되는지 확인
grep OPENAI_API_KEY .env
```

## 7. 자주 사용하는 명령어

**로그 확인**

```bash
# 전체 서비스 로그
docker compose -f docker-compose.dev.yml logs -f

# 특정 서비스 로그
docker compose -f docker-compose.dev.yml logs -f backend-api
docker compose -f docker-compose.dev.yml logs -f frontend

# 최근 50줄만
docker compose -f docker-compose.dev.yml logs --tail=50 backend-api
```

**서비스 재시작**

```bash
# 특정 서비스 재시작
docker compose -f docker-compose.dev.yml restart backend-api

# 전체 재시작
docker compose -f docker-compose.dev.yml restart

# 완전히 내렸다가 다시 시작
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d
```

**데이터베이스 마이그레이션**

```bash
# Alembic 마이그레이션 실행 (로컬 venv)
cd database
../.venv/bin/alembic upgrade head

# 또는 Makefile 사용
make migrate

# Docker 컨테이너 내부에서 실행
docker compose -f docker-compose.dev.yml run db-migrate
```

**데이터 파이프라인 실행**

```bash
# 로컬 실행 (venv)
source .venv/bin/activate
python -m datapipeline.run --backend live --market KR

# 테스트 실행 (LLM 미호출)
python -m datapipeline.run --backend mock

# Docker 컨테이너 내부에서 실행
docker exec dev-backend-api python -m datapipeline.run --backend live --market KR
```

**테스트 실행**

```bash
# 백엔드 단위 테스트
make test

# E2E 테스트
make test-e2e

# 특정 테스트 파일만 실행
pytest tests/unit/test_foo.py -v

# 특정 테스트 함수만 실행
pytest tests/unit/test_foo.py::test_bar -v
```

## 8. 트러블슈팅 FAQ

### 포트가 이미 사용 중입니다

```bash
# 포트를 사용하는 프로세스 확인
sudo lsof -i :5433   # PostgreSQL
sudo lsof -i :6379   # Redis
sudo lsof -i :8082   # Backend API
sudo lsof -i :3001   # Frontend

# 기존 Docker 컨테이너 중지
docker compose -f docker-compose.dev.yml down
```

### Docker 이미지 빌드 실패

```bash
# 캐시 없이 다시 빌드
docker compose -f docker-compose.dev.yml build --no-cache backend-api

# 또는 Makefile 사용
make build-api
```

### 데이터베이스 연결 실패

```bash
# PostgreSQL 컨테이너 상태 확인
docker compose -f docker-compose.dev.yml ps postgres

# PostgreSQL 로그 확인
docker compose -f docker-compose.dev.yml logs postgres

# psql로 직접 접속 테스트
psql -h localhost -p 5433 -U narative -d narrative_invest
# 비밀번호: password
```

### .env 파일이 로드되지 않습니다

```bash
# .env 파일 위치 확인 (프로젝트 루트에 있어야 함)
ls -la ~/adelie-investment/.env

# 파일 권한 확인
chmod 644 ~/adelie-investment/.env

# Docker Compose 재시작
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d
```

### 프론트엔드 핫 리로드가 작동하지 않습니다

```bash
# 볼륨 마운트 확인
docker compose -f docker-compose.dev.yml config | grep -A 5 volumes

# 컨테이너 재시작
docker compose -f docker-compose.dev.yml restart frontend

# Vite 개발 서버 로그 확인
docker compose -f docker-compose.dev.yml logs -f frontend
```

### Alembic 마이그레이션 오류

```bash
# 현재 마이그레이션 상태 확인
cd database
../.venv/bin/alembic current

# 마이그레이션 히스토리 확인
../.venv/bin/alembic history

# 특정 버전으로 다운그레이드
../.venv/bin/alembic downgrade <revision_id>

# 다시 업그레이드
../.venv/bin/alembic upgrade head
```

### API 키가 없어 AI 기능이 작동하지 않습니다

```bash
# .env 파일에 API 키 확인
grep -E '(OPENAI|PERPLEXITY|LANGCHAIN)_API_KEY' .env

# API 키 추가 후 백엔드 재시작
docker compose -f docker-compose.dev.yml restart backend-api
```

## 9. 다음 단계

- [02_git-workflow.md](./02_git-workflow.md) - Git 브랜치 전략 및 커밋 규칙
- [03_테스트가이드.md](./03_테스트가이드.md) - 테스트 작성 및 실행
- [04_배포가이드.md](./04_배포가이드.md) - deploy-test 서버 배포

역할별 상세 가이드:
- [A_backend개발.md](./A_backend개발.md) - FastAPI 백엔드 개발
- [B_chatbot개발.md](./B_chatbot개발.md) - LangGraph 튜터 에이전트 개발
- [C_frontend개발.md](./C_frontend개발.md) - React 프론트엔드 개발
- [D_pipeline개발.md](./D_pipeline개발.md) - 데이터 파이프라인 개발
- [E_인프라운영.md](./E_인프라운영.md) - Docker, LXD, CI/CD
