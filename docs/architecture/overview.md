# 아키텍처

Adelie Investment의 시스템 아키텍처 문서입니다.

## 전체 구조

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP/HTTPS
       ▼
┌──────────────────────────────────────────────┐
│         Frontend (React 19 + Vite)           │
│  - SPA with React Router                     │
│  - Nginx reverse proxy (/api/v1/* → backend) │
│  - Mobile-first (max-width: 480px)           │
└──────┬───────────────────────────────────────┘
       │ REST API + SSE
       ▼
┌──────────────────────────────────────────────┐
│       Backend API (FastAPI :8082)            │
│  - /api/v1/* (auth, keywords, cases, tutor)  │
│  - JWT authentication                        │
│  - SQLAlchemy async ORM                      │
└──────┬───────────────────────────────────────┘
       │
       ├─────────────┬──────────────┬──────────┐
       ▼             ▼              ▼          ▼
┌─────────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────┐
│ PostgreSQL  │ │  Redis  │ │  MinIO  │ │   Chatbot    │
│     15      │ │    7    │ │ (S3)    │ │  (LangGraph) │
└─────────────┘ └─────────┘ └─────────┘ └──────────────┘
                                              │
                                              ▼
                                        ┌──────────────┐
                                        │  Data Pipeline│
                                        │ (18-node)    │
                                        │  LangGraph   │
                                        └──────────────┘
```

## 디렉토리 구조

```
adelie-investment/
├── frontend/                # React 19 + Vite + Nginx (SPA)
│   ├── src/
│   │   ├── pages/           # 페이지 컴포넌트 (lazy-loaded)
│   │   ├── components/      # 재사용 컴포넌트
│   │   │   ├── common/      # 범용 컴포넌트
│   │   │   ├── domain/      # 도메인별 컴포넌트
│   │   │   ├── layout/      # 레이아웃 (AppHeader, BottomNav, ChatFAB)
│   │   │   ├── charts/      # Plotly 시각화
│   │   │   ├── tutor/       # 튜터 채팅 UI
│   │   │   └── trading/     # 모의투자 UI
│   │   ├── contexts/        # React Context (Theme, User, Portfolio, Tutor, Term)
│   │   ├── api/             # API 클라이언트 (도메인별 분리)
│   │   └── App.jsx          # 라우터 + Context Providers
│   ├── Dockerfile           # nginx 기반 프로덕션 이미지
│   └── nginx.conf           # /api/v1/* → backend-api:8082 프록시
│
├── fastapi/                 # FastAPI 백엔드 (:8082)
│   ├── app/
│   │   ├── models/          # SQLAlchemy 모델 (async, mapped_column)
│   │   ├── schemas/         # Pydantic v2 스키마
│   │   ├── api/routes/      # APIRouter (동적 임포트, prefix=/api/v1)
│   │   ├── services/        # 비즈니스 로직 (tutor_engine, keyword_service 등)
│   │   └── core/            # config, database, security (JWT)
│   ├── Dockerfile           # python:3.11-slim 기반
│   └── requirements.txt
│
├── chatbot/                 # AI 튜터 모듈
│   ├── agent/               # LangGraph 에이전트
│   │   └── tutor_agent.py   # State machine + tools
│   ├── tools/               # LangChain tools (search, briefing, comparison, visualization, glossary)
│   ├── services/            # term_highlighter (용어 하이라이트)
│   ├── prompts/             # 마크다운 프롬프트 템플릿 (tutor_system, tutor_beginner 등)
│   └── core/                # config, langsmith
│
├── datapipeline/            # 데이터 수집 + 브리핑 생성 파이프라인
│   ├── nodes/               # LangGraph 노드
│   │   ├── crawlers/        # 뉴스/리서치 크롤러
│   │   ├── screening/       # 종목 스크리닝
│   │   ├── curation/        # LLM 큐레이션
│   │   ├── interface1/      # 과거 유사사례 검색
│   │   ├── interface2/      # 종합 내러티브 생성
│   │   ├── interface3/      # 차트/용어집 생성
│   │   └── db_save/         # DB 저장
│   ├── data_collection/     # 데이터 수집 모듈
│   │   ├── news_crawler.py
│   │   ├── research_crawler.py
│   │   ├── screener.py
│   │   └── openai_curator.py
│   ├── ai/                  # LLM 클라이언트
│   │   ├── multi_provider_client.py  # OpenAI, Perplexity, Claude
│   │   └── llm_utils.py
│   ├── db/                  # DB 저장
│   │   └── writer.py        # asyncpg 직접 저장
│   ├── collectors/          # 레거시 pykrx 수집기 (FastAPI sys.path 호환)
│   ├── scripts/             # 레거시 파이프라인 스크립트
│   │   ├── seed_fresh_data_integrated.py
│   │   └── generate_cases.py
│   ├── prompts/templates/   # 9개 마크다운 프롬프트 템플릿
│   ├── graph.py             # LangGraph StateGraph 정의
│   ├── run.py               # 파이프라인 실행 진입점
│   ├── config.py            # 환경변수 기반 설정
│   ├── schemas.py           # Pydantic 스키마
│   └── Dockerfile           # python:3.11-slim 기반
│
├── database/                # DB 마이그레이션 + 스크립트
│   ├── alembic/             # Alembic migrations
│   │   ├── versions/        # 마이그레이션 파일
│   │   └── env.py           # 마이그레이션 설정
│   └── scripts/             # DB 관리 스크립트
│       ├── create_database.py
│       ├── reset_db.py
│       └── init_stock_listings.py
│
├── lxd/                     # LXD 인프라 구성
│   └── scripts/             # 컨테이너 관리 스크립트
│
└── tests/                   # 테스트
    ├── unit/                # 유닛 테스트 (pytest)
    ├── backend/             # API 통합 테스트
    ├── integration/         # E2E/Phase0 테스트
    └── load/                # Locust 부하 테스트
```

## Backend (FastAPI)

### Router Registration

모든 라우터는 `fastapi/app/main.py`에서 동적으로 임포트됩니다.

```python
# app/main.py에서 동적 임포트
for module_name in ["auth", "keywords", "cases", "tutor", ...]:
    try:
        module = importlib.import_module(f"app.api.routes.{module_name}")
        router = getattr(module, "router")
        app.include_router(router, prefix="/api/v1")
    except (ImportError, AttributeError):
        # 누락된 모듈은 gracefully skip (Docker 호환성)
        pass
```

모든 API는 `/api/v1` prefix 아래에 마운트됩니다.

### 인증 (Authentication)

JWT 토큰 기반 인증을 사용합니다.

```python
# app/core/security.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    # JWT 검증 후 User 객체 반환
    ...

async def get_current_user_optional(...) -> User | None:
    # 선택적 인증 (미인증 시 None 반환)
    ...
```

**적용 패턴:**
- `portfolio`, `learning`, `notification`: 필수 인증 (`get_current_user`)
- `tutor`: 선택적 인증 (`get_current_user_optional`, 미인증 시 포트폴리오 컨텍스트 생략)
- user_id path parameter 제거, JWT에서 추출

### Models

SQLAlchemy async ORM을 사용합니다.

```python
# app/models/user.py
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    ...
```

**규칙:**
- `Mapped[type]` + `mapped_column` 사용
- `app.core.database.Base` 상속
- 비동기 세션: `AsyncSession` from `sqlalchemy.ext.asyncio`

### Schemas

Pydantic v2를 사용합니다.

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}
```

### KST 날짜 처리

서버가 UTC로 실행되더라도 한국 시장 기준 날짜(KST)를 사용합니다.

```python
from datetime import timezone, timedelta

KST = timezone(timedelta(hours=9))

# 잘못된 방법 (서버 시간대 의존)
today = date.today()  # ❌

# 올바른 방법 (KST 기준)
today = datetime.now(KST).date()  # ✅
```

## Frontend (React 19)

### 페이지 라우팅

모든 페이지는 `React.lazy`로 lazy-load됩니다.

```jsx
// src/App.jsx
const HomePage = lazy(() => import('./pages/HomePage'));
const KeywordDetailPage = lazy(() => import('./pages/KeywordDetailPage'));

function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <PortfolioProvider>
          <TutorProvider>
            <TermProvider>
              <ErrorBoundary>
                <ToastProvider>
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/keyword/:id" element={<KeywordDetailPage />} />
                    ...
                  </Routes>
                </ToastProvider>
              </ErrorBoundary>
            </TermProvider>
          </TutorProvider>
        </PortfolioProvider>
      </UserProvider>
    </ThemeProvider>
  );
}
```

### Context Providers 계층

```
ThemeProvider (다크모드)
  └─ UserProvider (로그인 상태)
      └─ PortfolioProvider (포트폴리오 데이터)
          └─ TutorProvider (튜터 모달 상태)
              └─ TermProvider (용어 하이라이트)
                  └─ ErrorBoundary (에러 처리)
                      └─ ToastProvider (알림)
```

### API 레이어

도메인별로 분리된 API 클라이언트를 사용합니다.

```javascript
// src/api/client.js
export async function fetchJson(url, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// src/api/keywords.js
export async function getTodayKeywords() {
  return fetchJson('/api/v1/keywords/today');
}
```

**API Base URL:**
- Production: 빈 문자열 (nginx 프록시 사용)
- Development: `VITE_FASTAPI_URL` 환경변수 (예: `http://localhost:8082`)

### 스타일링

Tailwind CSS + CSS 변수 기반 테마를 사용합니다.

```css
/* src/index.css */
:root {
  --color-primary: #FF6B00;  /* Orange */
  --color-bg: #FFFFFF;
  --color-text: #1A1A1A;
}

.dark {
  --color-bg: #1A1A1A;
  --color-text: #E5E5E5;
}
```

**다크모드:** `class` 전략 사용 (`<html class="dark">`)

## Chatbot (LangGraph Agent)

### 구조

```
chatbot/
├── agent/tutor_agent.py     # LangGraph state machine
├── tools/                   # LangChain tools
│   ├── search_tool.py       # 웹 검색
│   ├── briefing_tool.py     # 오늘의 브리핑
│   ├── comparison_tool.py   # 과거-현재 비교
│   ├── visualization_tool.py # 차트 생성
│   └── glossary_tool.py     # 용어 검색
├── services/
│   └── term_highlighter.py  # 용어 하이라이트 서비스
└── prompts/
    ├── tutor_system.md      # 시스템 프롬프트
    └── tutor_beginner.md    # 초보자용 프롬프트
```

### SSE Streaming

FastAPI에서 튜터 응답을 SSE로 스트리밍합니다.

```python
# fastapi/app/services/tutor_engine.py
from chatbot.agent.tutor_agent import tutor_graph

async def stream_tutor_response(message: str, user_id: int):
    async for event in tutor_graph.astream_events({
        "messages": [message],
        "user_id": user_id,
    }):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            yield f"data: {json.dumps({'content': chunk.content})}\n\n"
```

프론트엔드에서 SSE 수신:

```javascript
// src/api/tutor.js
export async function* streamTutorChat(message) {
  const response = await fetch('/api/v1/tutor/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6));
      }
    }
  }
}
```

## Data Pipeline (18-node LangGraph)

### 파이프라인 흐름

```
[START]
   │
   ▼
[뉴스 크롤링] ──┐
[리서치 크롤링] ┤
   │           │
   ▼           │
[종목 스크리닝] ◄┘
   │
   ▼
[LLM 큐레이션]
   │
   ▼
[Interface 1: 과거 유사사례 검색]
   │
   ▼
[Interface 2: 종합 내러티브 생성]
   │
   ▼
[Interface 3: 차트/용어집 생성]
   │
   ▼
[DB 저장]
   │
   ▼
[END]
```

### 실행 방법

```bash
# 테스트 (LLM 미호출)
python -m datapipeline.run --backend mock

# 실서비스 (한국 시장)
python -m datapipeline.run --backend live --market KR
```

### AI Provider

`datapipeline/ai/multi_provider_client.py`에서 여러 LLM 제공자를 지원합니다.

```python
# datapipeline/ai/multi_provider_client.py
class MultiProviderClient:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.perplexity = OpenAI(
            api_key=os.getenv("PERPLEXITY_API_KEY"),
            base_url="https://api.perplexity.ai"
        )
        self.anthropic = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    async def chat(self, provider: str, model: str, messages: list):
        if provider == "openai":
            return await self.openai.chat.completions.create(...)
        elif provider == "perplexity":
            return await self.perplexity.chat.completions.create(...)
        elif provider == "anthropic":
            return await self.anthropic.messages.create(...)
```

### 프롬프트 템플릿

마크다운 기반 프롬프트를 사용합니다.

```markdown
<!-- datapipeline/prompts/templates/narrative_body.md -->
---
provider: openai
model: gpt-4-turbo-preview
temperature: 0.7
thinking: true
---

# 역할
당신은 금융 전문 작가입니다.

# 작업
과거 사례와 현재 이슈를 비교하여 종합 내러티브를 작성하세요.

# 입력
- 현재 키워드: {keyword}
- 과거 사례: {historical_case}
```

### DB 저장

`asyncpg`를 직접 사용하여 DB에 저장합니다 (ORM 미사용).

```python
# datapipeline/db/writer.py
import asyncpg

async def save_keyword(pool: asyncpg.Pool, data: dict):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO keywords (name, description, published_at)
            VALUES ($1, $2, $3)
        """, data["name"], data["description"], data["published_at"])
```

### KST 날짜 처리

Pipeline도 KST 기준 날짜를 사용합니다.

```python
# datapipeline/config.py
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

def kst_today():
    return datetime.now(KST).date()
```

## 팀 간 의존성

### API 스키마 변경

API 스키마가 변경되면 Frontend + Backend 동시 PR이 필요합니다.

**예시: 새로운 필드 추가**
1. Backend: `app/schemas/keyword.py`에서 `KeywordResponse`에 `trend_score: float` 추가
2. Backend: `app/api/routes/keywords.py`에서 응답에 `trend_score` 포함
3. Frontend: `src/api/keywords.js`에서 타입 업데이트 (TypeScript 사용 시)
4. Frontend: `src/components/KeywordCard.jsx`에서 `trend_score` 렌더링

### DB 스키마 변경

DB 스키마가 변경되면 Alembic migration + Pipeline writer 확인이 필요합니다.

**예시: 새로운 컬럼 추가**
1. Database: `alembic revision -m "add trend_score to keywords"`
2. Database: migration 파일에서 `op.add_column('keywords', sa.Column('trend_score', sa.Float()))`
3. Backend: `app/models/keyword.py`에서 `trend_score: Mapped[float]` 추가
4. Pipeline: `datapipeline/db/writer.py`에서 `INSERT` 쿼리에 `trend_score` 포함
5. Pipeline: `datapipeline/schemas.py`에서 `KeywordData`에 `trend_score` 추가

### SSE 이벤트 변경

Chatbot SSE 이벤트 포맷이 변경되면 Frontend와 동기화가 필요합니다.

**예시: 새로운 이벤트 타입 추가**
1. Chatbot: `chatbot/agent/tutor_agent.py`에서 `event_type: "tool_call"` 추가
2. Backend: `app/services/tutor_engine.py`에서 `tool_call` 이벤트 처리
3. Frontend: `src/components/tutor/ChatWindow.jsx`에서 `tool_call` 이벤트 렌더링

### 담당자별 주요 영역

| 담당자 | 주요 영역 | 영향 범위 |
|--------|-----------|-----------|
| 손영진 (팀장) | Frontend UI, 기획 | 모든 컴포넌트, API 클라이언트 |
| 정지훈 (AI) | Chatbot, Pipeline | LangGraph, AI tools, 프롬프트 |
| 안례진 (QA) | 테스트, 프롬프트 | 모든 테스트, AI 프롬프트 검증 |
| 허진서 (백엔드) | FastAPI 인증, DB | Auth routes, Models, Schemas |
| 도형준 (인프라) | Docker, CI/CD | Dockerfile, docker-compose, 배포 |

## 인프라

### 환경별 구성

| 환경 | 설명 | 구성 파일 |
|------|------|-----------|
| Development (로컬) | `make dev` | `docker-compose.dev.yml` |
| Staging (deploy-test) | `ssh deploy-test` (10.10.10.20) | `docker-compose.prod.yml` |
| Production | 미구성 | - |

### Development 환경

```yaml
# docker-compose.dev.yml
services:
  frontend:
    image: dorae222/adelie-frontend:dev
    ports: ["3000:80"]
    depends_on: [backend-api]

  backend-api:
    image: dorae222/adelie-backend-api:dev
    ports: ["8082:8082"]
    depends_on: [postgres, redis]

  postgres:
    image: postgres:15
    ports: ["5433:5432"]  # 로컬 5433 포트

  redis:
    image: redis:7
    ports: ["6379:6379"]
```

**실행:**
```bash
make dev          # Full stack
make dev-frontend # Frontend only
make dev-api      # Backend API only
make dev-down     # Stop
```

### Staging 환경 (deploy-test)

```yaml
# docker-compose.prod.yml
services:
  frontend:
    image: dorae222/adelie-frontend:latest
    ports: ["80:80", "443:443"]
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro

  backend-api:
    image: dorae222/adelie-backend-api:latest
    ports: ["8082:8082"]

  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio_data:/data
```

**배포:**
```bash
# 로컬에서 빌드 + 푸시
make build
make push

# deploy-test 서버에서 배포
ssh deploy-test
cd ~/adelie-investment
git pull
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Docker 이미지

| 이미지 | 태그 | 용도 |
|--------|------|------|
| dorae222/adelie-frontend | dev, latest | React SPA + nginx |
| dorae222/adelie-backend-api | dev, latest | FastAPI + Chatbot |
| dorae222/adelie-datapipeline | dev, latest | LangGraph Pipeline |

### 네트워크 구성

```
Internet
   │
   ▼
[Nginx Frontend :80, :443]
   │
   ├─ / → React SPA
   │
   └─ /api/v1/* → backend-api:8082
                      │
                      ├─ PostgreSQL :5432
                      ├─ Redis :6379
                      └─ MinIO :9000
```

### 데이터베이스

**Development (로컬):**
- Host: `localhost:5433`
- Database: `narrative_invest`
- User: `narative`

**Staging (deploy-test):**
- Host: `postgres:5432` (Docker 내부 네트워크)
- Database: `narrative_invest`
- User: `narative`

**마이그레이션:**
```bash
# 로컬
cd database && ../.venv/bin/alembic upgrade head

# Docker (dev)
docker compose -f docker-compose.dev.yml run db-migrate

# Docker (prod, deploy-test)
ssh deploy-test
docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"
```

## 데이터 흐름

### 1. 브리핑 생성 (Daily)

```
[Scheduler]
   │
   ▼
[datapipeline.run]
   │
   ├─ 뉴스 크롤링 (Naver Finance, 증권사)
   ├─ 리서치 크롤링 (증권사 리포트)
   ├─ 종목 스크리닝 (거래량, 등락률 기준)
   │
   ▼
[LLM 큐레이션]
   │
   ├─ OpenAI GPT-4 (종목 선별)
   ├─ Perplexity (웹 검색)
   │
   ▼
[내러티브 생성]
   │
   ├─ Interface 1: 과거 유사사례 검색
   ├─ Interface 2: 종합 내러티브 작성
   ├─ Interface 3: 차트/용어집 생성
   │
   ▼
[DB 저장]
   │
   └─ keywords, cases, glossary_terms 테이블
```

### 2. 사용자 요청 (실시간)

```
[Browser]
   │
   ▼
[GET /api/v1/keywords/today]
   │
   ├─ JWT 검증 (선택)
   ├─ PostgreSQL 조회
   │
   └─ Response: [{ id, name, description, ... }]
   │
   ▼
[사용자 키워드 클릭]
   │
   ▼
[GET /api/v1/cases/{id}]
   │
   ├─ JWT 검증 (선택)
   ├─ PostgreSQL 조회 (cases + glossary_terms)
   ├─ Redis 캐싱 (24시간)
   │
   └─ Response: { narrative, historical_case, charts, glossary }
```

### 3. 튜터 채팅 (SSE)

```
[Browser]
   │
   ▼
[POST /api/v1/tutor/chat]
   │
   ├─ JWT 검증 (선택)
   ├─ 포트폴리오 조회 (인증된 경우)
   │
   ▼
[LangGraph Tutor Agent]
   │
   ├─ 도구 선택 (search, briefing, comparison, visualization, glossary)
   ├─ LLM 호출 (OpenAI GPT-4)
   │
   ▼
[SSE Stream]
   │
   ├─ data: {"content": "안녕하세요"}
   ├─ data: {"content": "..."}
   │
   └─ data: {"done": true}
```

## 확장성 고려사항

### 1. 캐싱 전략

**Redis 캐싱:**
- 키워드 목록: 1시간 TTL
- 케이스 상세: 24시간 TTL
- 튜터 세션: 30분 TTL

```python
# app/services/cache.py
from redis import asyncio as aioredis

redis = aioredis.from_url(os.getenv("REDIS_URL"))

async def cache_keyword_list(date: str, data: list):
    await redis.setex(
        f"keywords:{date}",
        3600,  # 1시간
        json.dumps(data)
    )
```

### 2. 로드 밸런싱

현재 단일 인스턴스 구성이지만, 수평 확장 시 고려사항:

- **Stateless API**: 모든 세션은 Redis에 저장 (FastAPI 인스턴스는 stateless)
- **Database Connection Pool**: SQLAlchemy async pool 크기 조정
- **Nginx Load Balancer**: upstream 블록에 여러 backend-api 인스턴스 등록

```nginx
# nginx.conf (수평 확장 시)
upstream backend {
    server backend-api-1:8082;
    server backend-api-2:8082;
    server backend-api-3:8082;
}

location /api/v1/ {
    proxy_pass http://backend;
}
```

### 3. 모니터링

**Grafana + Prometheus (계획):**
- API 응답 시간
- DB 쿼리 성능
- Pipeline 실행 시간
- LLM API 호출 비용

**LangSmith (AI 모니터링):**
- Tutor agent 대화 기록
- Tool 사용 패턴
- LLM 응답 품질

## 보안

### 1. 인증/인가

- **JWT 토큰**: HS256 알고리즘, 24시간 유효기간
- **Refresh Token**: HttpOnly 쿠키 (7일 유효기간)
- **Password Hashing**: bcrypt (cost factor 12)

```python
# app/core/security.py
from passlib.context import CryptContext
import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    return jwt.encode(
        {**data, "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm="HS256"
    )
```

### 2. API 보안

- **CORS**: 프로덕션 도메인만 허용
- **Rate Limiting**: Redis 기반 (사용자당 분당 60회)
- **SQL Injection 방지**: SQLAlchemy parameterized queries
- **XSS 방지**: React 기본 escaping + DOMPurify (HTML 렌더링 시)

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://adelie-invest.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. 환경변수 관리

민감 정보는 `.env` 파일에 저장 (Git에서 제외).

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
CLAUDE_API_KEY=sk-ant-...
SECRET_KEY=random-secret-key
```

**프로덕션:** 환경변수는 Docker Compose secrets 또는 Kubernetes secrets로 관리.

## 트러블슈팅

### 1. DB 연결 실패

**증상:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**해결:**
1. PostgreSQL 컨테이너 상태 확인: `docker ps | grep postgres`
2. 포트 확인: 로컬은 5433, Docker 내부는 5432
3. DATABASE_URL 확인: `asyncpg` 드라이버 사용 여부
4. 방화벽: `sudo ufw allow 5432/tcp`

### 2. Frontend → Backend 통신 실패

**증상:**
```
Access to fetch at 'http://localhost:8082/api/v1/...' from origin 'http://localhost:3000' has been blocked by CORS
```

**해결:**
1. CORS 설정 확인: `app/main.py`의 `CORSMiddleware`
2. nginx 프록시 확인: `/api/v1/*` → `backend-api:8082`
3. 환경변수: `VITE_FASTAPI_URL` 설정 (로컬 개발 시)

### 3. Alembic 마이그레이션 실패

**증상:**
```
alembic.util.exc.CommandError: Target database is not up to date.
```

**해결:**
1. 현재 버전 확인: `alembic current`
2. 마이그레이션 히스토리: `alembic history`
3. 강제 업그레이드: `alembic upgrade head`
4. 롤백: `alembic downgrade -1`

### 4. Pipeline 실행 실패

**증상:**
```
datapipeline.exceptions.LLMAPIError: OpenAI API key not found
```

**해결:**
1. 환경변수 확인: `echo $OPENAI_API_KEY`
2. `.env` 파일 위치: 프로젝트 루트에 위치해야 함
3. Docker: `.env` 파일을 `docker-compose.yml`에서 `env_file`로 지정

## 참고 문서

- [개발 환경 설정](./02_개발환경설정.md)
- [Git 워크플로우](./03_Git워크플로우.md)
- [인프라 운영](./infra-ops.md)
- [API 문서](./API문서.md) (계획)
