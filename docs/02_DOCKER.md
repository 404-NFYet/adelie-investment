# 02. Docker 가이드

> Docker 기초부터 프로젝트 워크플로우까지 다룹니다.

## 목차
1. [Docker 기초](#1-docker-기초)
2. [프로젝트 Docker 구성](#2-프로젝트-docker-구성)
3. [일상 개발 워크플로우](#3-일상-개발-워크플로우)
4. [Docker Hub 이미지 관리](#4-docker-hub-이미지-관리)
5. [모니터링](#5-모니터링)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. Docker 기초

### 핵심 개념

- **이미지(Image)**: 실행 환경의 스냅샷. Dockerfile로 빌드하며, 불변(immutable).
- **컨테이너(Container)**: 이미지를 실행한 인스턴스. 생성/삭제가 자유로움.
- **볼륨(Volume)**: 컨테이너 삭제 후에도 유지되는 데이터 저장소.
- **Docker Compose**: 여러 컨테이너를 YAML로 정의하고 한 번에 관리.

### 자주 쓰는 명령어 10선

```bash
# 이미지
docker build -t name:tag .         # Dockerfile로 이미지 빌드
docker images                       # 로컬 이미지 목록
docker pull name:tag                # Docker Hub에서 이미지 다운로드

# 컨테이너
docker ps                           # 실행 중인 컨테이너 목록
docker ps -a                        # 전체 컨테이너 (중지 포함)
docker logs <container> -f          # 컨테이너 로그 실시간 추적
docker exec -it <container> bash    # 컨테이너 내부 접속

# Compose
docker compose up -d                # 백그라운드 실행
docker compose down                 # 중지 및 제거
docker compose ps                   # Compose 서비스 상태
```

---

## 2. 프로젝트 Docker 구성

### Docker Compose 파일 구조

| 파일 | 용도 | DB | 사용 시점 |
|------|------|-----|-----------|
| `docker-compose.dev.yml` | 개발 환경 | 로컬 Docker DB | `make dev` |
| `docker-compose.prod.yml` | 배포 (deploy-test) | 자체 포함 (풀스택) | `make deploy` |
| `docker-compose.test.yml` | 자동화 테스트 | 격리된 테스트 DB | `make test` |

### 서비스 관계도

```
┌─────────────┐    ┌──────────────┐
│  frontend   │───>│  backend-api │
│  :3001      │    │  :8082       │
│  (Nginx)    │    │  (Uvicorn)   │
└─────────────┘    └──────┬───────┘
                          │
                   ┌──────┴───────┐
                   │              │
              ┌────▼────┐  ┌─────▼────┐
              │ postgres │  │  redis   │
              │ :5432    │  │  :6379   │
              └──────────┘  └──────────┘
```

### docker-compose.dev.yml 서비스

| 서비스 | 포트 | 설명 | 핫 리로드 |
|--------|------|------|-----------|
| `postgres` | 5433 | PostgreSQL 15 (로컬) | - |
| `redis` | 6379 | Redis 7 | - |
| `frontend` | 3001 | React + Vite + Nginx | O (rebuild) |
| `backend-api` | 8082 | FastAPI + Uvicorn | O (`--reload`) |
| `ai-pipeline` | - | LangGraph 파이프라인 | X (프로필 전용) |
| `db-migrate` | - | Alembic 마이그레이션 | X (one-shot) |

### docker-compose.prod.yml (배포 환경)
위 서비스 + 인프라(PostgreSQL, Redis, MinIO) 모두 포함. 리소스 제한 설정 적용.

### docker-compose.test.yml (테스트 환경)

| 서비스 | 설명 |
|--------|------|
| `postgres-test` | 격리된 테스트 DB |
| `redis-test` | 격리된 테스트 캐시 |
| `test-backend` | pytest 실행 |
| `test-e2e` | Playwright E2E (프로필 전용) |

---

## 3. 일상 개발 워크플로우

### Makefile 명령어 요약

```bash
# 빌드
make build                # 전체 3개 이미지 빌드
make build-frontend       # 프론트엔드만
make build-api            # FastAPI만
make build TAG=v1.0       # 태그 지정

# 개발
make dev                  # 전체 개발 환경 (DB + Frontend + API)
make dev-frontend         # 프론트엔드만 (Docker)
make dev-api              # FastAPI만 (Docker)
make dev-down             # 중지

# 로컬 개발 (Docker 없이)
make dev-frontend-local   # cd frontend && npm run dev
make dev-api-local        # uvicorn (venv)

# 배포
make deploy               # 프로덕션 시작
make deploy-test          # deploy-test 서버 배포 (빌드→푸시→pull→재시작)
make deploy-down          # 프로덕션 중지

# 테스트
make test                 # 백엔드 pytest
make test-e2e             # Playwright E2E
make test-load            # Locust 부하 (40명)

# 유틸
make push                 # Docker Hub 푸시
make migrate              # Alembic 마이그레이션
make clean                # Docker 리소스 정리
```

### 시나리오별 워크플로우

#### 코드 수정 → 로컬 테스트

```bash
# 1. 코드 수정 (에디터에서)
# 2. Docker 개발 환경 실행
make dev

# 3. 확인
#    - Frontend: http://localhost:3001
#    - API Swagger: http://localhost:8082/docs

# 4. 중지
make dev-down
```

#### DB 모델 변경 (Alembic)

```bash
# 1. fastapi/app/models/ 에서 모델 수정
# 2. 마이그레이션 생성
cd database && ../.venv/bin/alembic revision --autogenerate -m "설명"

# 3. 마이그레이션 적용
../.venv/bin/alembic upgrade head

# 4. 팀원 공지 (Discord)
#    - migration 파일 커밋/푸시 → 팀원은 git pull 후 make migrate
```

#### 패키지 추가

```bash
# Python (FastAPI)
cd fastapi && pip install new-package && pip freeze > requirements.txt

# Node.js (Frontend)
cd frontend && npm install new-package
```

#### 빌드 확인 (배포 전)

```bash
# 로컬에서 prod 이미지 빌드 테스트
make build

# 이미지 크기 확인
docker images | grep adelie
```

---

## 4. Docker Hub 이미지 관리

### 이미지 목록

| 서비스 | Docker Hub 이미지 | Dockerfile |
|--------|------------------|------------|
| Frontend | `dorae222/adelie-frontend:TAG` | `frontend/Dockerfile` |
| FastAPI | `dorae222/adelie-backend-api:TAG` | `fastapi/Dockerfile` |
| AI Pipeline | `dorae222/adelie-ai-pipeline:TAG` | `datapipeline/Dockerfile` |

### 태깅 규칙

| 태그 | 용도 | 생성 시점 | 예시 |
|------|------|-----------|------|
| `latest` | 최신 안정 빌드 | develop → prod 머지 시 | `dorae222/adelie-frontend:latest` |
| `v{M.m.p}` | 릴리스 버전 | prod 태그 생성 시 | `dorae222/adelie-frontend:v0.9.1` |
| `dev-{SHA 7자}` | 개발 빌드 | 개발 중 테스트 시 | `dorae222/adelie-frontend:dev-bcd9660` |

### 배포 플로우

```
1. 코드 수정 + 커밋 (dev/{part} 브랜치)
   ↓
2. PR → develop 머지
   ↓
3. develop 테스트 확인
   ↓
4. develop → prod 릴리스 PR
   ↓
5. make build TAG=latest && make push TAG=latest
   ↓
6. make deploy-test  (deploy-test 서버에서 prod 브랜치 pull + 재시작)
```

### 개발 빌드 (개인 테스트용)

```bash
# 현재 커밋 SHA로 태깅
SHA=$(git rev-parse --short HEAD)
make build TAG=dev-$SHA
make push TAG=dev-$SHA
```

---

## 5. 모니터링

### 컨테이너 리소스

```bash
# 실시간 리소스 사용량 (CPU, 메모리, 네트워크)
docker stats

# 특정 서비스만
docker stats adelie-backend-api adelie-frontend
```

### 로그 확인

```bash
# 전체 서비스 로그
make logs

# 특정 서비스 (최근 100줄 + 실시간)
docker compose -f docker-compose.prod.yml logs --tail=100 -f backend-api

# 에러만 필터링
docker compose -f docker-compose.prod.yml logs backend-api 2>&1 | grep -i error
```

### 디스크 사용량

```bash
# Docker 전체 디스크 사용량 요약
docker system df

# 상세 (이미지별, 컨테이너별)
docker system df -v
```

---

## 6. 트러블슈팅

### 빌드 캐시 문제

```bash
# 캐시 없이 처음부터 빌드
docker compose -f docker-compose.dev.yml build --no-cache
```

### 컨테이너가 시작되지 않을 때

```bash
# 1. 상태 확인
docker compose -f docker-compose.dev.yml ps -a

# 2. 종료 로그 확인
docker compose -f docker-compose.dev.yml logs <서비스명>

# 3. 컨테이너 내부 진입 (디버깅)
docker compose -f docker-compose.dev.yml run --rm backend-api bash
```

### 특정 서비스만 재시작

```bash
docker compose -f docker-compose.dev.yml restart backend-api
```

### 포트 충돌

```bash
# 사용 중인 포트 확인
ss -tlnp | grep -E '3001|8082|5432|6379'

# Docker 컨테이너 포트 매핑 확인
docker port <container_name>
```

### DB 연결 문제

```bash
# PostgreSQL 컨테이너 상태
docker compose -f docker-compose.dev.yml ps postgres

# 연결 테스트
docker compose -f docker-compose.dev.yml exec postgres pg_isready

# infra-server 연결 테스트 (shared 모드)
pg_isready -h 10.10.10.10 -p 5432 -U narative
```

### 디스크 공간 부족

```bash
# 사용하지 않는 리소스 정리 (안전)
make clean

# 강력 정리 (모든 미사용 이미지/볼륨 삭제)
docker system prune -af --volumes
```

### 이미지 pull 실패

```bash
# Docker Hub 인증 확인
docker login

# 수동 pull
docker pull dorae222/adelie-frontend:latest

# 로컬 레지스트리 사용 (Docker Hub 장애 시)
make push-local TAG=latest
# 이후 docker-compose에서 이미지를 10.10.10.10:5000/adelie-*:latest 로 변경
```
