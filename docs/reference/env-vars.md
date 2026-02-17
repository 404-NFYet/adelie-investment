# 환경변수 가이드

> 프로젝트의 모든 환경변수를 정리한 문서.
> `.env` 파일은 절대 git에 커밋하지 않는다.

## 1. 모드별 환경변수 차이

| 환경변수 | shared (infra-server) | local (Docker) | deploy-test (prod) |
|----------|----------------------|----------------|-------------------|
| `DATABASE_URL` | `postgresql+asyncpg://narative:password@10.10.10.10:5432/narrative_invest` | `postgresql+asyncpg://narative:password@localhost:5433/narrative_invest` | `postgresql+asyncpg://narative:password@postgres:5432/narrative_invest` (docker-compose 내부) |
| `REDIS_URL` | `redis://10.10.10.10:6379/1` | `redis://localhost:6379/1` | `redis://redis:6379/1` (docker-compose 내부) |
| `MINIO_ENDPOINT` | `http://10.10.10.10:9000` | 미사용 | `http://minio:9000` (docker-compose 내부) |
| `VITE_FASTAPI_URL` | `http://10.10.10.20:8082` (deploy-test API 사용) | 빈 문자열 (Vite proxy 사용) | 빈 문자열 (nginx 프록시) |
| `ENVIRONMENT` | `development` | `development` | `production` |
| `DEBUG` | `true` | `true` | `false` |

### shared 모드 (infra-server 공유 DB)

팀원 전원이 `10.10.10.10`의 공유 PostgreSQL/Redis/MinIO에 연결하여 개발한다. 데이터가 공유되므로 파괴적인 작업(테이블 DROP, 대량 DELETE 등)은 반드시 팀원에게 사전 공지한다.

### local 모드 (로컬 Docker DB)

`docker-compose.dev.yml`로 로컬에 PostgreSQL(:5433), Redis(:6379)를 띄운다. 독립적인 개발 환경이므로 자유롭게 데이터를 조작할 수 있다.

### deploy-test 모드 (배포 테스트 서버)

`10.10.10.20` 서버에서 `docker-compose.prod.yml`로 전체 스택을 운영한다. 모든 인프라가 docker-compose 네트워크 내부에서 컨테이너명(`postgres`, `redis`, `minio`)으로 통신한다.

---

## 2. 전체 환경변수 목록

### 포트 설정

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `FASTAPI_PORT` | `8082` | FastAPI 서버 포트 | Backend |
| `FRONTEND_PORT` | `3001` | Vite 개발 서버 포트 | Frontend (dev only) |

### 데이터베이스 (PostgreSQL)

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://narative:password@postgres:5432/narrative_invest` | 비동기 DB 연결 URL (asyncpg) | Backend, Pipeline |
| `SYNC_DATABASE_URL` | (자동 변환) | 동기 DB 연결 URL (psycopg2) | Alembic migration |
| `DB_HOST` | `postgres` | DB 호스트 | Backend, Pipeline |
| `DB_PORT` | `5432` | DB 포트 | Backend, Pipeline |
| `DB_NAME` | `narrative_invest` | DB 이름 | Backend, Pipeline |
| `DB_USER` | `narative` | DB 사용자 | Backend, Pipeline |
| `DB_PASSWORD` | `password` | DB 비밀번호 | Backend, Pipeline |

> **참고**: `DATABASE_URL`에 `+asyncpg`가 포함되어 있다. Alembic은 동기 드라이버가 필요하므로 `SYNC_DATABASE_URL`을 자동 변환하거나, `alembic/env.py`에서 `+asyncpg`를 제거하여 사용한다.

### Redis

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `REDIS_URL` | `redis://redis:6379/1` | Redis 연결 URL | Backend (캐시, rate limit) |
| `REDIS_HOST` | `redis` | Redis 호스트 | Backend |
| `REDIS_PORT` | `6379` | Redis 포트 | Backend |

### MinIO (S3 호환 오브젝트 스토리지)

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `MINIO_ENDPOINT` | `http://minio:9000` | MinIO 엔드포인트 | Backend (차트 HTML 저장) |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO 접근 키 | Backend |
| `MINIO_SECRET_KEY` | `minioadmin123` | MinIO 비밀 키 | Backend |

### AI API 키

| 변수명 | 기본값 | 필수 | 설명 | 사용처 |
|--------|--------|------|------|--------|
| `OPENAI_API_KEY` | - | **필수** | OpenAI API 키 (튜터, 차트 생성 등) | Backend, Chatbot, Pipeline |
| `PERPLEXITY_API_KEY` | - | **필수** | Perplexity API 키 (웹 검색 큐레이션) | Pipeline |
| `LANGCHAIN_API_KEY` | - | **필수** | LangSmith API 키 (트레이싱) | Chatbot, Pipeline |
| `CLAUDE_API_KEY` | - | 선택 | Anthropic API 키 (Writer 에이전트, 시각화 코드 생성) | Backend, Pipeline |

### AI 모델 설정

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `OPENAI_MAIN_MODEL` | `gpt-4o-mini` | 기본 OpenAI 모델 | Backend (튜터) |
| `OPENAI_VISION_MODEL` | `gpt-4o` | 비전 모델 | Backend |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | 임베딩 모델 | Backend |
| `OPENAI_FALLBACK_MODEL` | `gpt-5.2` | Pipeline JSON 복구/Anthropic 대체 호출 시 사용하는 OpenAI 모델 | Pipeline |
| `OPENAI_TIMEOUT_SECONDS` | `180` | OpenAI 요청 타임아웃(초). 장문 검증/생성 타임아웃 완화용 | Backend, Pipeline |
| `PERPLEXITY_TIMEOUT_SECONDS` | `60` | Perplexity 요청 타임아웃(초) | Pipeline |
| `PERPLEXITY_MODEL` | `sonar-pro` | Perplexity 모델 | Pipeline |
| `DEFAULT_MODEL` | `claude-sonnet-4-20250514` | 레거시/일부 스크립트 기본 모델 (프롬프트 frontmatter가 우선) | Pipeline |
| `CHART_MODEL` | `gpt-5-mini` | 차트 생성 모델 | Pipeline |

> Interface 2/3 내러티브 생성 프롬프트(`page_purpose`, `historical_case`, `narrative_body`, `3_*`)는 현재 frontmatter 기준으로 `provider=openai`, `model=gpt-5.2`를 기본 사용한다.
> OpenAI 호출 실패 시 동일 모델로 1회 재시도하며, 재시도도 실패하면 해당 호출은 실패로 처리한다.

### LangSmith (트레이싱)

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `LANGCHAIN_TRACING_V2` | `true` | LangSmith 트레이싱 활성화 | Chatbot, Pipeline |
| `LANGCHAIN_PROJECT` | `adelie-pipeline` | LangSmith 프로젝트명 | Chatbot, Pipeline |
| `LANGCHAIN_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API 엔드포인트 | Chatbot, Pipeline |

### 인증 (JWT)

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `JWT_SECRET` | `CHANGE-THIS-IN-PRODUCTION` | JWT 서명 비밀키 | Backend |
| `JWT_ALGORITHM` | `HS256` | JWT 알고리즘 | Backend |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 토큰 만료 시간 (분) | Backend |

### 한국투자증권 API (선택)

| 변수명 | 기본값 | 필수 | 설명 | 사용처 |
|--------|--------|------|------|--------|
| `KIS_APP_KEY` | - | 선택 | KIS 앱 키 (모의매매) | Backend (trading) |
| `KIS_APP_SECRET` | - | 선택 | KIS 앱 시크릿 | Backend (trading) |

### 애플리케이션 설정

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `ENVIRONMENT` | `development` | 실행 환경 (development/production) | Backend |
| `DEBUG` | `true` | 디버그 모드 | Backend |
| `LOG_LEVEL` | `INFO` | 로그 레벨 | Backend |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3001,http://localhost:8082` | CORS 허용 도메인 | Backend |

### Frontend 전용 (Vite)

| 변수명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| `VITE_FASTAPI_URL` | 빈 문자열 | API 베이스 URL (빈 값이면 프록시/nginx 사용) | Frontend |

> **주의**: Vite에서는 `VITE_` 접두사가 있는 환경변수만 클라이언트 번들에 포함된다. Frontend에서 `.env`를 로드할 때 `vite.config.js`의 `envDir`이 프로젝트 루트(`../`)를 가리키므로, 루트 `.env` 파일의 `VITE_*` 변수를 읽는다.

---

## 3. API 키 관리

### 원칙

- **모든 팀원이 동일한 API 키를 사용**한다 (개인 키 사용 금지)
- `.env` 파일은 **절대 git에 커밋하지 않는다** (`.gitignore`에 포함)
- API 키는 Discord DM 또는 비공개 채널을 통해 공유한다
- 키 교체 시 Discord #infra 채널에 즉시 공지한다

### 신규 팀원 온보딩

1. `.env.example`을 `.env`로 복사: `cp .env.example .env`
2. Discord에서 실제 API 키를 받아 `.env`에 입력
3. 필수 키 3개: `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `LANGCHAIN_API_KEY`
4. DB 접속 정보는 사용할 모드(shared/local)에 따라 `DATABASE_URL` 수정

### 키 유출 시 대응

1. 즉시 해당 API 대시보드에서 키 revoke
2. 새 키 발급 후 Discord 공유
3. 모든 팀원 `.env` 업데이트
4. deploy-test 서버 `.env`도 업데이트 후 서비스 재시작

---

## 4. LangSmith 설정

### 현재 설정

모든 팀원이 단일 프로젝트를 사용한다:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=adelie-pipeline
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=lsv2_xxx  # 실제 키
```

### 향후 팀원별 분리 (계획)

개발 중 트레이싱이 섞이는 것을 방지하기 위해 팀원별 프로젝트 분리가 가능하다:

```env
# 정지훈 (AI 개발)
LANGCHAIN_PROJECT=dev-jihoon

# 안례진 (AI QA)
LANGCHAIN_PROJECT=dev-ryejin

# 프로덕션 (deploy-test)
LANGCHAIN_PROJECT=adelie-pipeline
```

분리 시 LangSmith 대시보드에서 프로젝트를 미리 생성할 필요는 없다 (자동 생성됨).

---

## 5. 환경변수 변동 프로세스

새로운 환경변수를 추가하거나 기존 값을 변경할 때:

### 추가 절차

1. **`.env.example` 업데이트**: 변수명, 기본값, 설명 주석 추가
2. **이 문서(`11_ENV_VARS.md`) 업데이트**: 해당 섹션에 변수 추가
3. **Discord #infra 공지**: 변수명, 용도, 값 설정 방법 안내
4. **각 팀원**: 자신의 `.env` 파일에 변수 추가
5. **deploy-test 서버**: `ssh deploy-test`로 접속하여 `.env` 수정 후 서비스 재시작

### 삭제 절차

1. 코드에서 해당 환경변수 참조 모두 제거
2. `.env.example`에서 삭제
3. 이 문서에서 삭제
4. Discord 공지 (각 팀원 `.env`에서 제거 안내)

### docker-compose 환경변수 우선순위

Docker Compose에서 환경변수는 다음 우선순위로 적용된다:

1. `docker-compose.*.yml`의 `environment:` 섹션 (최우선)
2. `.env` 파일 (`env_file: .env`)
3. 호스트 시스템 환경변수

따라서 `docker-compose.dev.yml`에서 `DATABASE_URL`을 명시적으로 설정하면 `.env`의 값을 덮어쓴다. 이를 통해 개발 환경에서는 로컬 컨테이너 DB를, 배포 환경에서는 내부 네트워크 DB를 자동으로 사용한다.
