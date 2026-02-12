# 02. Docker 워크플로우 가이드

> Docker Compose를 활용한 개발/배포/테스트 환경 안내입니다.

## 목차
1. [Docker Compose 파일 구조](#1-docker-compose-파일-구조)
2. [서비스 구성](#2-서비스-구성)
3. [Makefile 명령어](#3-makefile-명령어)
4. [개발 시나리오별 사용법](#4-개발-시나리오별-사용법)
5. [이미지 네이밍 및 빌드](#5-이미지-네이밍-및-빌드)
6. [개발 → 배포 플로우](#6-개발--배포-플로우)
7. [환경 변수 참조](#7-환경-변수-참조)
8. [트러블슈팅](#8-트러블슈팅)

---

## 1. Docker Compose 파일 구조

| 파일 | 용도 | DB 연결 | 사용 시점 |
|------|------|---------|-----------|
| `docker-compose.dev.yml` | 개발자 로컬 개발 | infra-server 공유 | `make dev` |
| `docker-compose.prod.yml` | 배포 (deploy-test, AWS) | 자체 포함 (풀스택) | `make deploy` |
| `docker-compose.test.yml` | 자동화 테스트 | 격리된 테스트 DB | `make test` |
| `infra/docker-compose.yml` | 인프라 전용 | - | infra-server에서만 |

## 2. 서비스 구성

### docker-compose.dev.yml (개발 환경)
| 서비스 | 포트 | 설명 | 핫 리로드 |
|--------|------|------|-----------|
| `frontend` | 3001 | React + Vite | O (Vite HMR) |
| `backend-api` | 8082 | FastAPI + Uvicorn | O (`--reload`) |
| `backend-spring` | 8083 | Spring Boot | X |
| `ai-pipeline` | - | LangGraph 워커 | X (프로필 전용) |

### docker-compose.prod.yml (배포 환경)
위 서비스 + 인프라(PostgreSQL, Redis, Neo4j, MinIO) 모두 포함.
리소스 제한 설정 (PostgreSQL 8GB, Neo4j 4GB 등).

### docker-compose.test.yml (테스트 환경)
| 서비스 | 설명 |
|--------|------|
| `postgres-test` | 격리된 테스트 DB |
| `redis-test` | 격리된 테스트 캐시 |
| `test-backend` | pytest 실행 |
| `test-e2e` | Playwright E2E (프로필 전용) |

## 3. Makefile 명령어

```bash
# === 빌드 ===
make build                # 전체 4개 서비스 이미지 빌드
make build TAG=v1.0       # 태그 지정 빌드
make build-frontend       # 프론트엔드만
make build-api            # FastAPI만

# === 개발 환경 ===
make dev                  # 전체 개발 환경 시작
make dev-frontend         # 프론트엔드만
make dev-api              # FastAPI만
make dev-down             # 개발 환경 중지

# === 배포 환경 ===
make deploy               # 프로덕션 환경 시작
make deploy-down          # 프로덕션 환경 중지
make deploy-logs          # 프로덕션 로그 확인

# === 테스트 ===
make test                 # 백엔드 테스트
make test-backend         # pytest
make test-e2e             # Playwright E2E
make test-load            # Locust 부하 테스트 (40 사용자)
make test-pipeline        # 파이프라인 검증

# === 이미지 푸시 ===
make push TAG=v1.0        # Docker Hub (dorae222/*)
make push-local TAG=v1.0  # 로컬 레지스트리 (10.10.10.10:5000)

# === 유틸리티 ===
make logs                 # 전체 로그 tail
make migrate              # Alembic DB 마이그레이션
make clean                # Docker 이미지/볼륨 정리
make help                 # 전체 명령어 목록
```

## 4. 개발 시나리오별 사용법

### 프론트엔드만 개발할 때
```bash
make dev-frontend
# → http://localhost:3001 접속
# → src/ 파일 수정 시 Vite HMR으로 즉시 반영
# → API 호출은 .env의 VITE_FASTAPI_URL로 프록시
```

### FastAPI 백엔드만 개발할 때
```bash
make dev-api
# → http://localhost:8082/docs 접속 (Swagger UI)
# → fastapi/app/ 파일 수정 시 자동 재시작 (--reload)
```

### 전체 서비스 통합 개발
```bash
make dev
# → 프론트엔드(3001) + FastAPI(8082) + Spring Boot(8083) 동시 실행
# → infra-server(10.10.10.10)의 DB 공유
```

### AI 파이프라인 실행
```bash
# 개발 환경에서 AI 파이프라인 프로필 활성화
docker compose -f docker-compose.dev.yml --profile pipeline up -d
```

## 5. 이미지 네이밍 및 빌드

| 서비스 | Docker Hub 이미지 | Dockerfile 위치 |
|--------|------------------|-----------------|
| Frontend | `dorae222/adelie-frontend:TAG` | `frontend/Dockerfile` |
| FastAPI | `dorae222/adelie-backend-api:TAG` | `fastapi/Dockerfile` |
| Spring Boot | `dorae222/adelie-backend-spring:TAG` | `springboot/Dockerfile` |
| AI Pipeline | `dorae222/adelie-ai-pipeline:TAG` | `datapipeline/Dockerfile` |

빌드 아키텍처:
- **Frontend**: Multi-stage (Node.js builder → Nginx runtime)
- **FastAPI**: Python 3.11-slim, 4 Uvicorn workers
- **Spring Boot**: Multi-stage (Gradle builder → JRE 17 runtime)
- **AI Pipeline**: Python 3.11-slim, 워커 서비스

## 6. 개발 → 배포 플로우

```
1. 코드 수정 (dev 컨테이너에서 작업)
   ↓
2. make dev 로 로컬 테스트
   ↓
3. git commit & push (develop 브랜치)
   ↓ (CI: lint + test 자동 실행)
4. make build TAG=v1.1
   ↓
5. make push TAG=v1.1
   ↓
6. deploy-test에서:
   REGISTRY=dorae222 TAG=v1.1 docker compose -f docker-compose.prod.yml up -d
   ↓
7. 데이터 초기화 (필요 시):
   docker exec -e OPENAI_API_KEY="$KEY" adelie-backend-api python /app/generate_cases.py
```

## 7. 환경 변수 참조

전체 환경 변수는 `.env.example` 파일에 정의되어 있습니다.
주요 섹션:

| 섹션 | 변수 예시 | 용도 |
|------|-----------|------|
| 포트 | `FASTAPI_PORT`, `FRONTEND_PORT` | 서비스 포트 바인딩 |
| 프론트엔드 | `VITE_FASTAPI_URL` | API 엔드포인트 |
| 데이터베이스 | `DATABASE_URL`, `REDIS_URL` | DB 연결 문자열 |
| AI | `OPENAI_API_KEY`, `OPENAI_MAIN_MODEL` | LLM 모델 설정 |
| 인증 | `JWT_SECRET`, `JWT_ALGORITHM` | JWT 토큰 설정 |

## 8. 트러블슈팅

### 빌드 캐시 문제
```bash
# 캐시 없이 처음부터 빌드
docker compose -f docker-compose.dev.yml build --no-cache
```

### 컨테이너 로그 확인
```bash
# 특정 서비스 로그 (실시간 추적)
docker compose -f docker-compose.dev.yml logs backend-api -f

# 최근 100줄만
docker compose -f docker-compose.dev.yml logs --tail=100 backend-api
```

### 특정 서비스만 재시작
```bash
docker compose -f docker-compose.dev.yml restart backend-api
```

### 디스크 공간 부족
```bash
# 사용하지 않는 Docker 리소스 정리
make clean
# 또는 직접
docker system prune -af --volumes
```

### 네트워크 문제 (infra-server 연결 불가)
```bash
# infra-server 핑 테스트
ping 10.10.10.10

# PostgreSQL 직접 연결 테스트
docker run --rm postgres:16 pg_isready -h 10.10.10.10 -p 5432
```
