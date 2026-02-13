# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adelie Investment ("History Repeats Itself") is an AI-powered financial education platform that matches current Korean stock market events with historical cases. Mobile-first (max-width: 480px), Korean language UI.

## Build & Run Commands

### Development (Docker, connects to infra-server 10.10.10.10)
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

### Backend
- **FastAPI** (`fastapi/`, `:8082`, `/api/v1/*`): 모든 API — auth, keywords, cases, tutor chat, glossary, trading, visualization, narrative

### Frontend Routing via Nginx
The frontend Docker image uses nginx as a reverse proxy. All `/api/v1/*` routes proxy to `backend-api:8082`. Legacy `/api/auth/*` paths are rewritten to `/api/v1/auth/*`. The SPA uses React Router with code splitting (`React.lazy`).

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

### Python 실행 경로

| 환경 | Python 버전 | 경로 |
|------|------------|------|
| 로컬 (venv) | 3.12.3 | `.venv/bin/python` |
| 로컬 (시스템) | 3.12.3 | `/usr/bin/python3` |
| Docker (fastapi, datapipeline) | 3.11 | `python:3.11-slim` 이미지 |

- 로컬 실행 시 반드시 `.venv` 활성화 후 실행: `source .venv/bin/activate` 또는 `.venv/bin/python` 직접 사용
- Docker 내부는 Python 3.11, 로컬은 3.12 — 버전 차이 주의

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

## Skills (Claude Code CLI)

| 명령 | 설명 |
|------|------|
| `/deploy [frontend\|api\|all]` | 서비스 빌드 → Docker Hub 푸시 → deploy-test 배포 |
| `/test [unit\|backend\|integration\|e2e\|all]` | 테스트 실행 (pytest/playwright) |
| `/seed [collect\|generate\|all]` | 데이터 파이프라인 실행 (시장 데이터 수집 + 케이스 생성) |
| `/migrate [upgrade\|current\|history\|revision\|downgrade]` | Alembic DB 마이그레이션 관리 |

## Environment Variables

Required API keys in `.env`: `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `LANGCHAIN_API_KEY`
DB defaults are provided but can be overridden: `DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`, `MINIO_ENDPOINT`
