# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adelie Investment ("History Repeats Itself") is an AI-powered financial education platform that matches current Korean stock market events with historical cases. Mobile-first (max-width: 480px), Korean language UI.

## Build & Run Commands

### Development (Docker, connects to infra-server 10.10.10.10)
```bash
make dev                    # Full stack: frontend + backend-api + backend-spring
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

### Spring Boot
```bash
cd springboot && ./gradlew bootRun   # http://localhost:8083
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

### Data Pipeline (run inside backend-api container on deploy-test)
```bash
# Step 1: Collect market data + seed keywords
docker exec adelie-backend-api python /app/scripts/seed_fresh_data_integrated.py

# Step 2: Generate historical cases via LLM (requires OPENAI_API_KEY in .env)
docker exec adelie-backend-api python /app/scripts/generate_cases.py
```

## Architecture

### Directory Structure
```
adelie-investment/
├── frontend/           # React 19 + Vite + Nginx (SPA)
├── fastapi/            # FastAPI backend (AI/Data API)
│   └── app/            # app.models, app.schemas, app.api.routes, app.services
├── springboot/         # Spring Boot backend (Auth, CRUD)
├── chatbot/            # AI 튜터 모듈 (LangGraph agent + tools)
│   ├── agent/          # tutor_agent, prompts, checkpointer
│   ├── tools/          # LangChain tools (glossary, search, visualization...)
│   ├── services/       # term_highlighter
│   ├── prompts/        # 튜터 전용 프롬프트 템플릿
│   └── core/           # config, langsmith
├── datapipeline/       # 데이터 수집 + 케이스 생성 파이프라인
│   ├── scripts/        # pipeline scripts (seed, generate, verify)
│   ├── ai/             # AI 서비스 (multi_provider_client, ai_service)
│   ├── collectors/     # 데이터 수집기 (stock, report, financial)
│   └── prompts/        # 파이프라인 프롬프트 템플릿
├── database/           # DB 마이그레이션 + 스크립트
│   ├── alembic/        # Alembic migrations
│   └── scripts/        # create_database, reset_db, init_stock_listings
├── lxd/                # LXD 인프라 구성
└── tests/              # 테스트
    ├── unit/           # 유닛 테스트
    ├── backend/        # API 통합 테스트
    └── integration/    # E2E/Phase0 테스트
```

### Dual Backend
- **FastAPI** (`fastapi/`, `:8082`, `/api/v1/*`): AI/Data API — keywords, cases, tutor chat, glossary, trading, visualization, narrative
- **Spring Boot** (`springboot/`, `:8083`, `/api/auth/*`, `/api/user/*`, etc.): Auth (JWT), CRUD, bookmarks, user settings

### Frontend Routing via Nginx
The frontend Docker image uses nginx as a reverse proxy. All `/api/v1/*` routes proxy to `backend-api:8082`, and `/api/auth/*`, `/api/user/*`, `/api/bookmarks/*` etc. proxy to `backend-spring:8080`. The SPA uses React Router with code splitting (`React.lazy`).

### Key Data Flow
1. `datapipeline/scripts/seed_fresh_data_integrated.py` collects real market data via **pykrx** → writes to `daily_briefings` + `briefing_stocks`
2. `datapipeline/scripts/generate_cases.py` reads keywords from `daily_briefings`, calls **OpenAI gpt-4o-mini** to generate historical case matches → writes to `historical_cases` + `case_matches` + `case_stock_relations`
3. Frontend fetches `/api/v1/keywords/today` → displays keyword cards → user clicks → `/api/v1/cases/{id}` for full narrative

### Chatbot (`chatbot/`)
LangGraph-based tutor agent with SSE streaming. Structured as:
- `agent/tutor_agent.py` — LangGraph state machine with tools (search, briefing, comparison, visualization, glossary)
- `services/term_highlighter.py` — 용어 하이라이트 서비스
- `prompts/` — 마크다운 기반 프롬프트 템플릿 (tutor_system, tutor_beginner 등)
- Imported by `fastapi/app/services/tutor_engine.py` at runtime

The tutor modal is globally available in the frontend via `TutorContext` + `ChatFAB`.

### Data Pipeline (`datapipeline/`)
- `scripts/` — 키워드 수집, 케이스 생성, 검증 스크립트
- `ai/` — LLM 프로바이더 클라이언트 (OpenAI, Perplexity, Claude) + 파이프라인 AI 서비스
- `collectors/` — pykrx 주가 수집기, 네이버 리포트 크롤러
- `prompts/` — 파이프라인 프롬프트 (planner, writer, reviewer 등)

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

| Service | Dev (infra-server) | Prod (docker-compose.prod.yml) |
|---------|-------------------|-------------------------------|
| PostgreSQL (pgvector) | 10.10.10.10:5432 | `postgres` container |
| Redis 7 | 10.10.10.10:6379 | `redis` container |
| Neo4j 5 | 10.10.10.10:7687 | `neo4j` container |
| MinIO | 10.10.10.10:9000 | `minio` container |

Deploy-test server: `10.10.10.20` (SSH alias: `deploy-test`)

## Git Rules
- 커밋 메시지에 Co-Authored-By 절대 포함하지 않음
- AI 도구 사용 흔적을 커밋/PR에 남기지 않음

## Git Workflow
- git worktree 3~5개 병렬 운영 (feature별 별도 worktree + Claude 세션)
- 브랜치 전략: `main` ← `develop` ← `feature/*`
- worktree 생성: `git worktree add ../adelie-{feature} develop`

## Skills (Claude Code CLI)

| 명령 | 설명 |
|------|------|
| `/deploy [frontend\|api\|spring\|all]` | 서비스 빌드 → Docker Hub 푸시 → deploy-test 배포 |
| `/test [unit\|backend\|integration\|e2e\|all]` | 테스트 실행 (pytest/playwright) |
| `/seed [collect\|generate\|all]` | 데이터 파이프라인 실행 (시장 데이터 수집 + 케이스 생성) |
| `/migrate [upgrade\|current\|history\|revision\|downgrade]` | Alembic DB 마이그레이션 관리 |

## Environment Variables

Required API keys in `.env`: `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `LANGCHAIN_API_KEY`
DB defaults are provided but can be overridden: `DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`, `MINIO_ENDPOINT`
