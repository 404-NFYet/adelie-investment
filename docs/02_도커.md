# Docker 사용 가이드

이 문서는 Adelie Investment 프로젝트의 Docker 기반 개발 환경 사용법을 설명합니다.

## 1. 기본 명령어

### 개발 환경 시작
```bash
# 전체 스택 시작 (frontend + backend-api + postgres + redis)
make dev

# 개별 서비스만 시작
make dev-frontend  # 프론트엔드만
make dev-api       # 백엔드 API만
```

### 개발 환경 종료
```bash
# 모든 컨테이너 정지 및 제거
make dev-down

# 또는 직접 명령어 사용
docker compose -f docker-compose.dev.yml down
```

### 로그 확인
```bash
# 모든 서비스 로그 실시간 확인
docker compose -f docker-compose.dev.yml logs -f

# 특정 서비스만
docker compose -f docker-compose.dev.yml logs -f backend-api
docker compose -f docker-compose.dev.yml logs -f frontend
```

### 컨테이너 상태 확인
```bash
# 실행 중인 컨테이너 목록
docker compose -f docker-compose.dev.yml ps

# 모든 컨테이너 (정지된 것 포함)
docker compose -f docker-compose.dev.yml ps -a
```

### 서비스 재시작
```bash
# 특정 서비스 재시작
docker compose -f docker-compose.dev.yml restart backend-api
docker compose -f docker-compose.dev.yml restart frontend

# 모든 서비스 재시작
docker compose -f docker-compose.dev.yml restart
```

## 2. 서비스별 설명

### postgres
- **역할**: PostgreSQL 15 데이터베이스
- **포트**: 5433 (호스트) → 5432 (컨테이너)
- **볼륨**: `postgres_data` (데이터 영구 저장)
- **접속**: `psql -h localhost -p 5433 -U narative -d narrative_invest`
- **비고**: 로컬 개발용 DB, production과 독립적

### redis
- **역할**: Redis 7 캐시 서버
- **포트**: 6379 (호스트) → 6379 (컨테이너)
- **볼륨**: `redis_data` (데이터 영구 저장)
- **접속**: `redis-cli -h localhost -p 6379`
- **용도**: 세션 캐싱, Celery 메시지 브로커

### frontend
- **역할**: React 19 + Vite 개발 서버
- **포트**: 3001 (호스트) → 3001 (컨테이너)
- **볼륨 마운트**:
  - `./frontend/src:/app/src` (소스 코드)
  - `./frontend/public:/app/public` (정적 파일)
- **HMR**: 코드 수정 시 자동 반영 (Hot Module Replacement)
- **접속**: http://localhost:3001
- **이미지**: `dorae222/adelie-frontend-dev:latest`

### backend-api
- **역할**: FastAPI 백엔드 서버
- **포트**: 8082 (호스트) → 8082 (컨테이너)
- **볼륨 마운트**:
  - `./fastapi/app:/app/app` (FastAPI 앱)
  - `./chatbot:/app/chatbot` (튜터 에이전트)
  - `./datapipeline:/app/datapipeline` (데이터 파이프라인)
  - `./database:/app/database` (Alembic 마이그레이션)
- **자동 재시작**: `uvicorn --reload` 옵션으로 코드 수정 시 자동 재시작
- **API 문서**: http://localhost:8082/docs
- **이미지**: `dorae222/adelie-backend-api:latest`

### ai-pipeline
- **역할**: 데이터 수집 및 브리핑 생성 파이프라인
- **프로필**: `pipeline` (기본 실행되지 않음)
- **실행**: `docker compose --profile pipeline up ai-pipeline`
- **볼륨 마운트**: `./datapipeline:/app` (전체 파이프라인 코드)
- **용도**: 뉴스/리서치 크롤링 → 스크리닝 → LLM 큐레이션 → DB 저장
- **이미지**: `dorae222/adelie-ai-pipeline:latest`

### db-migrate
- **역할**: Alembic DB 마이그레이션 실행
- **프로필**: `migrate` (기본 실행되지 않음)
- **실행**: `docker compose --profile migrate run db-migrate`
- **용도**: 스키마 변경 적용
- **비고**: backend-api 이미지 재사용, command만 다름

## 3. Docker Hub 워크플로우

### 최신 이미지 가져오기
다른 팀원이 이미지를 업데이트한 경우:

```bash
# 모든 서비스 이미지 pull
docker compose -f docker-compose.dev.yml pull

# 특정 서비스만
docker compose -f docker-compose.dev.yml pull backend-api
docker compose -f docker-compose.dev.yml pull frontend

# pull 후 재시작
docker compose -f docker-compose.dev.yml up -d
```

### 이미지 빌드 및 공유
로컬에서 Dockerfile을 수정한 경우:

```bash
# 전체 빌드 및 푸시
make build  # 빌드
make push   # Docker Hub에 푸시

# 개별 서비스만
make build-frontend  # 프론트엔드 빌드
make build-api       # 백엔드 빌드

# 직접 명령어 (frontend 예시)
docker build -t dorae222/adelie-frontend-dev:latest -f frontend/Dockerfile.dev .
docker push dorae222/adelie-frontend-dev:latest

# 직접 명령어 (backend-api 예시)
docker build -t dorae222/adelie-backend-api:latest -f fastapi/Dockerfile .
docker push dorae222/adelie-backend-api:latest
```

**주의**: Docker Hub 푸시는 `dorae222` 계정 권한 필요. 인프라 담당자에게 문의.

## 4. 프로필 사용법

### pipeline 프로필
데이터 파이프라인 실행:

```bash
# 18노드 LangGraph 브리핑 파이프라인 실행
docker compose --profile pipeline up ai-pipeline

# 백그라운드 실행
docker compose --profile pipeline up -d ai-pipeline

# 로그 확인
docker compose logs -f ai-pipeline
```

### migrate 프로필
DB 마이그레이션 실행:

```bash
# Alembic upgrade head
docker compose --profile migrate run db-migrate

# 또는 Makefile 사용
make migrate

# 특정 버전으로 마이그레이션
docker compose --profile migrate run db-migrate alembic upgrade <revision>

# 마이그레이션 이력 확인
docker compose --profile migrate run db-migrate alembic history
```

## 5. 개별 서비스 재시작/재빌드

### 코드 수정 후 재시작이 필요한 경우

**frontend, backend-api**: 일반적으로 자동 반영되므로 재시작 불필요

**자동 반영되지 않는 경우** (패키지 설치, 환경변수 변경 등):

```bash
# 특정 서비스만 재시작
docker compose -f docker-compose.dev.yml restart backend-api

# 재빌드 후 재시작 (Dockerfile 변경 시)
docker compose -f docker-compose.dev.yml up -d --build backend-api

# 강제 재빌드 (캐시 무시)
docker compose -f docker-compose.dev.yml build --no-cache backend-api
docker compose -f docker-compose.dev.yml up -d backend-api
```

### 의존성 추가 후 재빌드
```bash
# 프론트엔드: package.json 변경 시
docker compose -f docker-compose.dev.yml build --no-cache frontend
docker compose -f docker-compose.dev.yml up -d frontend

# 백엔드: requirements.txt 변경 시
docker compose -f docker-compose.dev.yml build --no-cache backend-api
docker compose -f docker-compose.dev.yml up -d backend-api
```

## 6. 트러블슈팅

### Orphan containers 경고
```
WARNING: Found orphan containers (adelie-backend-spring) for this project.
```

**원인**: 이전 docker-compose.yml에 있던 서비스가 현재 파일에 없음

**해결**:
```bash
# orphan 컨테이너 제거
docker compose -f docker-compose.dev.yml down --remove-orphans

# 또는 직접 제거
docker rm -f adelie-backend-spring
```

### 포트 충돌
```
Error: Bind for 0.0.0.0:5433 failed: port is already allocated
```

**해결**:
```bash
# 포트 사용 중인 프로세스 확인
sudo lsof -i :5433

# 기존 컨테이너 정리
docker compose -f docker-compose.dev.yml down

# 모든 중지된 컨테이너 제거
docker container prune
```

### 볼륨 정리
DB를 완전히 초기화하려는 경우:

```bash
# 컨테이너 및 볼륨 삭제
docker compose -f docker-compose.dev.yml down -v

# 특정 볼륨만 삭제
docker volume rm adelie-investment_postgres_data
docker volume rm adelie-investment_redis_data

# 사용하지 않는 볼륨 일괄 정리
docker volume prune
```

### 이미지 캐시 문제
이전 이미지 레이어가 남아있어 변경사항이 반영되지 않는 경우:

```bash
# 빌드 캐시 무시하고 재빌드
docker compose -f docker-compose.dev.yml build --no-cache

# 전체 이미지 재빌드 후 실행
docker compose -f docker-compose.dev.yml up -d --build --force-recreate

# 사용하지 않는 이미지 정리
docker image prune -a
```

### 컨테이너 내부 접속
디버깅이 필요한 경우:

```bash
# bash 쉘 실행
docker compose -f docker-compose.dev.yml exec backend-api bash
docker compose -f docker-compose.dev.yml exec frontend sh

# 특정 명령어 실행
docker compose -f docker-compose.dev.yml exec backend-api python -c "import sys; print(sys.path)"
docker compose -f docker-compose.dev.yml exec postgres psql -U narative -d narrative_invest
```

### 네트워크 문제
서비스 간 통신이 되지 않는 경우:

```bash
# 네트워크 재생성
docker compose -f docker-compose.dev.yml down
docker network prune
docker compose -f docker-compose.dev.yml up -d

# 네트워크 확인
docker network ls
docker network inspect adelie-investment_default
```

## 참고 자료
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [프로젝트 CLAUDE.md](/CLAUDE.md) - 전체 아키텍처 및 명령어 참조
- [Makefile](/Makefile) - 자주 사용하는 명령어 단축키
