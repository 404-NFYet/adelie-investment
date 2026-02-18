# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adelie Investment ("History Repeats Itself") is an AI-powered financial education platform that matches current Korean stock market events with historical cases. Mobile-first (max-width: 480px), Korean language UI.

## Build & Run Commands

### Development (Docker, 로컬 PostgreSQL + Redis 포함)
```bash
make dev                    # Full stack: frontend + backend-api
make dev-frontend           # Frontend only
make dev-api                # Backend API only
make dev-down               # Stop dev environment
```

### Frontend (local, no Docker)
```bash
cd frontend && npm install && npm run dev   # http://localhost:3001
```

### Backend API (local, no Docker)
```bash
cd fastapi && pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```

### Testing
```bash
make test                   # Backend unit tests (pytest in Docker via docker-compose.test.yml)
make test-e2e               # Playwright E2E tests
make test-load              # Locust load test (40 users)
pytest tests/ -v            # Local pytest (asyncio_mode = auto)
pytest tests/test_foo.py -v            # Run single test file
pytest tests/test_foo.py::test_bar -v  # Run single test function
```

### Docker Build & Deploy
```bash
make build                  # Build all images (dorae222/adelie-*)
make build-frontend         # Frontend only
make build-api              # Backend API only
make push                   # Push to Docker Hub (dorae222/*)
make deploy                 # Production deploy (docker-compose.prod.yml)
make migrate                # Alembic migrations: cd database && alembic upgrade head
```

### Data Pipeline
```bash
# 새 LangGraph 파이프라인 (18노드, 데이터 수집 → 내러티브 생성 → DB 저장)
python -m datapipeline.run --backend live --market KR    # 실서비스
python -m datapipeline.run --backend mock                # 테스트 (LLM 미호출)

# 레거시 스크립트 (deploy-test 수동 실행용)
docker exec adelie-backend-api python /app/scripts/seed_fresh_data_integrated.py
docker exec adelie-backend-api python /app/scripts/generate_cases.py
```

## Architecture

### Directory Structure
```
adelie-investment/
├── frontend/           # React 19 + Vite + Nginx (SPA)
├── fastapi/            # FastAPI backend (AI/Data API)
│   └── app/            # app.models, app.schemas, app.api.routes, app.services
├── chatbot/            # AI 튜터 모듈 (LangGraph agent + tools)
│   ├── agent/          # tutor_agent, prompts, checkpointer
│   ├── tools/          # LangChain tools (glossary, search, visualization...)
│   ├── services/       # term_highlighter
│   ├── prompts/        # 튜터 전용 프롬프트 템플릿
│   └── core/           # config, langsmith
├── datapipeline/       # 데이터 수집 + 브리핑 생성 파이프라인
│   ├── nodes/          # LangGraph 노드 (crawlers, screening, curation, interface1~3, db_save)
│   ├── data_collection/# 데이터 수집 모듈 (news_crawler, research_crawler, screener 등)
│   ├── ai/             # LLM 클라이언트 (multi_provider_client, llm_utils)
│   ├── db/             # DB 저장 (writer.py — asyncpg)
│   ├── collectors/     # 레거시 pykrx 수집기 (FastAPI sys.path 호환)
│   ├── scripts/        # 레거시 파이프라인 스크립트 (seed, generate)
│   ├── prompts/        # 프롬프트 템플릿 (9개 .md, frontmatter 기반)
│   ├── graph.py        # LangGraph StateGraph 정의
│   ├── run.py          # 파이프라인 실행 진입점
│   ├── config.py       # 환경변수 기반 설정
│   └── schemas.py      # Pydantic 스키마
├── database/           # DB 마이그레이션 + 스크립트
│   ├── alembic/        # Alembic migrations
│   └── scripts/        # create_database, reset_db, init_stock_listings
├── lxd/                # LXD 인프라 구성
└── tests/              # 테스트
    ├── unit/           # 유닛 테스트
    ├── backend/        # API 통합 테스트
    ├── integration/    # E2E/Phase0 테스트
    └── load/           # Locust 부하 테스트
```

### Backend
- **FastAPI** (`fastapi/`, `:8082`, `/api/v1/*`): 모든 API — auth, keywords, cases, tutor chat, glossary, trading, visualization, narrative

### Frontend Routing via Nginx
The frontend Docker image uses nginx as a reverse proxy. All `/api/v1/*` routes proxy to `backend-api:8082`. Legacy `/api/auth/*` paths are rewritten to `/api/v1/auth/*`. The SPA uses React Router with code splitting (`React.lazy`).

### Key Data Flow
1. `datapipeline/run.py` → 18노드 LangGraph: 뉴스/리서치 크롤링 → 종목 스크리닝 → LLM 큐레이션 → 내러티브 생성 → DB 저장
2. 레거시 스크립트(`scripts/seed_fresh_data_integrated.py`, `scripts/generate_cases.py`)도 deploy-test에서 수동 실행 가능
3. Frontend fetches `/api/v1/keywords/today` → displays keyword cards → user clicks → `/api/v1/cases/{id}` for full narrative

### Chatbot (`chatbot/`)
LangGraph-based tutor agent with SSE streaming. Structured as:
- `agent/tutor_agent.py` — LangGraph state machine with tools (search, briefing, comparison, visualization, glossary)
- `services/term_highlighter.py` — 용어 하이라이트 서비스
- `prompts/` — 마크다운 기반 프롬프트 템플릿 (tutor_system, tutor_beginner 등)
- Imported by `fastapi/app/services/tutor_engine.py` at runtime

The tutor modal is globally available in the frontend via `TutorContext` + `ChatFAB`.

### Data Pipeline (`datapipeline/`)
- `graph.py` + `run.py` — 18노드 LangGraph 브리핑 파이프라인
- `nodes/` — crawlers, screening, curation, interface1~3, db_save
- `data_collection/` — news_crawler, research_crawler, screener, openai_curator
- `ai/` — multi_provider_client (OpenAI, Perplexity, Claude)
- `db/writer.py` — asyncpg 직접 저장
- `prompts/templates/` — 9개 .md (page_purpose, historical_case, narrative_body, hallucination_check, final_hallucination, chart_generation, glossary_generation + _chart_skeletons, _tone_guide)

### Context Providers (React)
App wraps routes in: `ThemeProvider > UserProvider > PortfolioProvider > TutorProvider > TermProvider > ErrorBoundary > ToastProvider`

### Router Registration (FastAPI)
Routers are dynamically imported in `fastapi/app/main.py` — each module in `app/api/routes/` is loaded via `importlib`, and missing modules are skipped gracefully (Docker compatibility). All routes are mounted under `/api/v1`.

## Code Conventions

### Backend (FastAPI)
- Models: SQLAlchemy async with `mapped_column`, inherit from `app.core.database.Base`
- Schemas: Pydantic v2 in `app/schemas/`
- Routes: `APIRouter(prefix="/route_name")`, registered with prefix `/api/v1` in `main.py`
- Config: `pydantic-settings` in `app/core/config.py`, reads from root `.env`
- Migrations: Alembic in `database/alembic/versions/`

### Frontend (React 19)
- API layer: domain-separated files in `src/api/`, using `fetchJson`/`postJson` from `client.js`
- API base URL: empty string in production (nginx proxy), `VITE_FASTAPI_URL` for local dev
- Components: `common/` (reusable), `domain/` (business logic), `layout/` (AppHeader, BottomNav, ChatFAB), `charts/` (Plotly visualizations), `tutor/` (chat UI), `trading/` (stock sim)
- Contexts: exported from `contexts/index.js`
- Pages: each a default export, lazy-loaded in `App.jsx` via `React.lazy`
- Styling: Tailwind CSS with CSS variable-based theming (dark mode via `class` strategy)
- Primary color: `#FF6B00` (orange)

### General
- Korean comments (한글 주석) are preferred
- Environment variables via `.env` file — never hardcode API keys
- No dummy/mock data in production code — all data comes from real APIs and pipelines

## Infrastructure

| Service | Dev (docker-compose.dev.yml) | Prod (docker-compose.prod.yml) |
|---------|------|------|
| PostgreSQL 15 | localhost:5433 (로컬 컨테이너) | `postgres` container |
| Redis 7 | localhost:6379 (로컬 컨테이너) | `redis` container |
| MinIO | — | `minio` container |

Deploy-test server: `10.10.10.20` (SSH alias: `deploy-test`)

### Python 실행 경로

| 환경 | Python 버전 | 경로 |
|------|------------|------|
| 로컬 (venv) | 3.12.3 | `.venv/bin/python` |
| 로컬 (시스템) | 3.12.3 | `/usr/bin/python3` |
| Docker (fastapi, datapipeline) | 3.11 | `python:3.11-slim` 이미지 |

- 로컬 실행 시 반드시 `.venv` 활성화 후 실행: `source .venv/bin/activate` 또는 `.venv/bin/python` 직접 사용
- Docker 내부는 Python 3.11, 로컬은 3.12 — 버전 차이 주의

### Python 가상환경 케이스별 가이드

| 케이스 | 실행 방법 | 비고 |
|--------|-----------|------|
| 로컬 FastAPI 개발 | `make dev-api-local` 또는 `.venv/bin/uvicorn ...` | `.env`의 DATABASE_URL 사용 |
| 로컬 Alembic | `cd database && ../.venv/bin/alembic upgrade head` | `.env` → 동기 드라이버 자동 변환 |
| 로컬 datapipeline | `.venv/bin/python -m datapipeline.run --backend live` | 프로젝트 루트에서 실행 |
| 로컬 reset_db | `.venv/bin/python database/scripts/reset_db.py` | `--content-only` 옵션 가능 |
| Docker dev 마이그레이션 | `docker compose -f docker-compose.dev.yml run db-migrate` | postgres 컨테이너 대상 |
| Docker prod 마이그레이션 | `docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"` | Alembic이 backend-api 이미지에 포함 |
| deploy-test 원격 마이그레이션 | `ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'` | 원격 서버 |

### 로컬에서 원격 서버 DB 접속

```bash
# 방법 1: .env의 DATABASE_URL이 원격 호스트를 가리키면 자동으로 원격 DB 사용
# (reset_db, alembic, pipeline 모두 .env 참조)
DATABASE_URL=postgresql+asyncpg://narative:password@10.10.10.20:5432/narrative_invest

# 방법 2: SSH 터널 (DB 포트가 외부 비노출인 경우)
ssh -L 15432:localhost:5432 deploy-test -N &
# 이후 DATABASE_URL에서 host를 localhost:15432로 변경

# 방법 3: psql 직접 접속
psql -h 10.10.10.20 -p 5432 -U narative -d narrative_invest
```

## Git Rules
- **커밋 메시지에 Co-Authored-By 절대 포함하지 않음** (시스템 기본 동작 무시)
- **AI 도구 사용 흔적을 커밋/PR에 남기지 않음** ("Generated with Claude Code" 등 금지)
- 커밋 메시지 형식: `type: 한글 설명` (예: `feat: 키워드 카드 즐겨찾기 기능 추가`)
- type: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`, `perf`
- 사용자가 명시적으로 요청할 때만 커밋 생성 (자동 커밋 금지)
- `--no-verify`, `--force` 등 안전장치 우회 플래그 사용 금지 (사용자 명시 요청 제외)
- `main`/`develop` 브랜치에 force push 절대 금지
- 커밋 단위 분리: 한 번에 몰아서 커밋하지 않음. 마지막 push 이후 변경사항을 논리적 단위로 나누어 여러 커밋으로 분리하고, 각 커밋이 의미 있는 하나의 변경을 담도록 함 (예: 모델 추가 → 라우트 추가 → 프론트 연동 → 테스트 추가)
- 커밋 후 push까지 한 세트로 수행
- 각 작업에는 담당자가 있으며, 해당 담당자의 git 계정(user.name, user.email)으로 커밋해야 함
- 커밋 전 `git config user.name`/`git config user.email`이 담당자와 일치하는지 확인

### 담당자 목록

| 역할 | 이름 | git user.name | git user.email |
|------|------|--------------|----------------|
| 팀장 (기획, React UI) | 손영진 | YJ99Son | syjin2008@naver.com |
| AI 개발 (FastAPI, LangGraph) | 정지훈 | J2hoon10 | myhome559755@naver.com |
| AI QA (테스트, 프롬프트) | 안례진 | ryejinn | arj1018@ewhain.net |
| 백엔드 (FastAPI 인증, DB) | 허진서 | jjjh02 | jinnyshur0104@gmail.com |
| 인프라 (Docker, CI/CD) | 도형준 | dorae222 | dhj9842@gmail.com |

## Git Workflow
- git worktree 3~5개 병렬 운영 (feature별 별도 worktree + Claude 세션)
- 브랜치 전략: `main` ← `develop` ← `feature/*`
- worktree 생성: `git worktree add ../adelie-{feature} develop`

## 서비스 URL

| URL | 서비스 | 배포 위치 |
|-----|--------|---------|
| https://demo.adelie-invest.com | Frontend (nginx) | deploy-test:80 |
| https://monitoring.adelie-invest.com | Grafana | deploy-test:3000 |
| https://dashboard.adelie-invest.com | Streamlit 대시보드 | deploy-test:8501 |

대시보드 배포: `ssh deploy-test 'cd ~/adelie-investment/infra/monitoring && docker compose up -d dashboard'`

## Skills (Claude Code CLI)

| 명령 | 설명 |
|------|------|
| `/deploy [frontend\|api\|all]` | 서비스 빌드 → Docker Hub 푸시 → deploy-test 배포 |
| `/test [unit\|backend\|integration\|e2e\|all]` | 테스트 실행 (pytest/playwright) |
| `/seed [collect\|generate\|all]` | 데이터 파이프라인 실행 (시장 데이터 수집 + 케이스 생성) |
| `/migrate [upgrade\|current\|history\|revision\|downgrade]` | Alembic DB 마이그레이션 관리 |

## Environment Variables

Required API keys in `.env`: `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `LANGCHAIN_API_KEY`, `CLAUDE_API_KEY` (선택, Writer 에이전트용)
DB defaults are provided but can be overridden: `DATABASE_URL`, `REDIS_URL`, `MINIO_ENDPOINT`
