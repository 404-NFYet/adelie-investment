# 01. 개발 환경 설정 가이드

> 신규 팀원을 위한 단계별 설정 안내입니다.

## 목차
1. [LXD 컨테이너 접속](#1-lxd-컨테이너-접속)
2. [Docker 확인](#2-docker-확인)
3. [Docker Hub 로그인](#3-docker-hub-로그인)
4. [프로젝트 클론 및 설정](#4-프로젝트-클론-및-설정)
5. [환경 변수 설정](#5-환경-변수-설정)
6. [개발 서버 실행](#6-개발-서버-실행)
7. [데이터 초기화](#7-데이터-초기화)
8. [접속 확인](#8-접속-확인)
9. [이미지 빌드/배포](#9-이미지-빌드배포)
10. [트러블슈팅](#10-트러블슈팅)

---

## 1. LXD 컨테이너 접속

각 팀원에게 LXD 컨테이너가 할당되어 있습니다.

| 팀원 | 호스트 | IP |
|------|--------|-----|
| dev-j2hoon10 | LXD | 10.10.10.11 |
| dev-jjjh02 | LXD | 10.10.10.12 |
| dev-ryejinn | LXD | 10.10.10.13 |
| dev-yj99son | LXD | 10.10.10.14 |
| dev-hj | LXD | 10.10.10.15 |

```bash
# SSH 접속
ssh ubuntu@10.10.10.{번호}

# SSH 키 설정 (최초 1회 - 비밀번호 입력 생략 가능)
ssh-keygen -t ed25519 -C "your-email@example.com"
ssh-copy-id ubuntu@10.10.10.{번호}
```

## 2. Docker 확인

```bash
docker --version          # Docker 29.2.1 이상 필요
docker compose version    # Docker Compose V2 필요
```

Docker가 설치되지 않은 경우 팀장에게 문의하세요.

## 3. Docker Hub 로그인

```bash
# 팀장에게 DOCKER_PAT(Personal Access Token)을 요청하세요
echo "$DOCKER_PAT" | docker login -u dorae222 --password-stdin
```

## 4. 프로젝트 클론 및 설정

```bash
cd ~
git clone https://github.com/404-NFYet/adelie-investment.git
cd adelie-investment
```

## 5. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일의 주요 변수:

| 변수 | 설명 | 기본값 | 수정 필요 |
|------|------|--------|-----------|
| `OPENAI_API_KEY` | OpenAI API 키 | (없음) | **필수** - 팀장에게 요청 |
| `DATABASE_URL` | PostgreSQL 연결 | infra-server | 변경 불필요 |
| `REDIS_URL` | Redis 연결 | infra-server | 변경 불필요 |
| `NEO4J_URI` | Neo4j 연결 | infra-server | 변경 불필요 |
| `MINIO_ENDPOINT` | MinIO 연결 | infra-server | 변경 불필요 |
| `FASTAPI_PORT` | FastAPI 포트 | 8082 | 충돌 시 변경 |
| `FRONTEND_PORT` | 프론트엔드 포트 | 3001 | 충돌 시 변경 |
| `JWT_SECRET` | JWT 시크릿 | 기본값 | 개발 시 변경 불필요 |
| `PERPLEXITY_API_KEY` | Perplexity 검색 | (없음) | AI 파이프라인 사용 시 필요 |
| `LANGCHAIN_API_KEY` | LangSmith 트레이싱 | (없음) | 선택 (디버깅 시 유용) |

> **중요**: `.env` 파일은 `.gitignore`에 포함되어 있으므로 커밋되지 않습니다. API 키를 절대 커밋하지 마세요.

## 6. 개발 서버 실행

```bash
# 전체 서비스 실행 (프론트엔드 + FastAPI + Spring Boot)
make dev

# 특정 서비스만 실행
make dev-frontend     # 프론트엔드만 (포트 3001)
make dev-api          # FastAPI만 (포트 8082)

# 서비스 중지
make dev-down
```

실행 후 약 30초~1분 대기하면 모든 서비스가 준비됩니다.

## 7. 데이터 초기화 (최초 1회)

데이터베이스는 infra-server(10.10.10.10)에서 공유되지만, 초기 데이터가 없을 수 있습니다.

```bash
# Step 1: 시장 데이터 수집 (pykrx로 오늘의 급등/급락/거래량 종목 수집)
docker exec adelie-backend-api python /app/scripts/seed_fresh_data.py
# 출력 예시:
#   수집 날짜: 20260208
#   전체 종목: 2847
#   시장: KOSPI 2815.32, KOSDAQ 893.12
#   키워드 5개 생성
#   daily_briefings: id=1
#   briefing_stocks: 15건
#   === 완료 ===

# Step 2: 역사적 사례 생성 (LLM 기반, OPENAI_API_KEY 필요)
docker exec -e OPENAI_API_KEY="$OPENAI_API_KEY" adelie-backend-api python /app/generate_cases.py
# 이 과정은 약 2~5분 소요됩니다.
```

## 8. 접속 확인

| 서비스 | URL | 설명 |
|--------|-----|------|
| 프론트엔드 | http://localhost:3001 | React 앱 |
| FastAPI Docs | http://localhost:8082/docs | Swagger UI |
| Spring Boot | http://localhost:8083 | Spring API |
| **데모 사이트** | https://demo.adelie-invest.com | deploy-test 배포판 |

## 9. 이미지 빌드/배포

```bash
# Docker 이미지 빌드
make build TAG=v1.0      # 전체 4개 서비스

# Docker Hub에 푸시
make push TAG=v1.0       # dorae222/* 레지스트리

# 로컬 레지스트리 푸시 (LXD 내부용)
make push-local TAG=v1.0 # 10.10.10.10:5000
```

## 10. 트러블슈팅

### 포트 충돌
```bash
# 사용 중인 포트 확인
ss -tlnp | grep 3001
# 해결: .env에서 포트 번호 변경 후 make dev 재실행
```

### 컨테이너가 시작되지 않을 때
```bash
# 로그 확인
make logs
# 또는 특정 서비스
docker compose -f docker-compose.dev.yml logs backend-api -f
```

### 빌드 캐시 문제
```bash
docker compose -f docker-compose.dev.yml build --no-cache
```

### DB 연결 실패
```bash
# infra-server 연결 확인
ping 10.10.10.10
# PostgreSQL 연결 테스트
docker exec adelie-backend-api python -c "from app.core.database import engine; print('OK')"
```

## 인프라 구조

```
┌─────────────────────────────────────────┐
│ infra-server (10.10.10.10)              │
│ ├── PostgreSQL 16 + pgvector (5432)     │
│ ├── Redis 7 (6379)                      │
│ ├── Neo4j 5 (7687/7474)                │
│ └── MinIO (9000/9001)                   │
├─────────────────────────────────────────┤
│ dev-* 컨테이너 (각 팀원)                │
│ ├── Frontend (3001)                     │
│ ├── FastAPI (8082)                      │
│ └── Spring Boot (8083)                  │
│    → infra-server DB 공유               │
├─────────────────────────────────────────┤
│ deploy-test (10.10.10.20)               │
│ ├── 풀스택 (자체 DB 포함)               │
│ └── Cloudflare Tunnel → demo.adelie-invest.com │
└─────────────────────────────────────────┘
```
