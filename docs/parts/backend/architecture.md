# Backend 아키텍처

> FastAPI 앱 구조, 라우터 동적 등록, SQLAlchemy 패턴, JWT 인증, API 라우트, Alembic을 다룬다.

---

## 디렉토리 구조

```
fastapi/
├── Dockerfile              # Python 3.11-slim 기반 Docker 이미지
├── requirements.txt        # 의존성
└── app/
    ├── main.py             # FastAPI 앱 진입점 (라우터 동적 등록, 미들웨어)
    ├── __init__.py
    ├── core/               # 핵심 설정
    │   ├── config.py       # pydantic-settings 기반 설정 (Settings)
    │   ├── database.py     # SQLAlchemy async engine + session
    │   ├── auth.py         # JWT 인증 의존성 (get_current_user)
    │   ├── limiter.py      # slowapi rate limiter
    │   ├── logging.py      # 구조화된 로깅
    │   └── scheduler.py    # APScheduler 데일리 파이프라인 스케줄러
    ├── models/             # SQLAlchemy ORM 모델
    │   ├── user.py         # 사용자
    │   ├── briefing.py     # 일일 브리핑
    │   ├── narrative.py    # 내러티브
    │   ├── historical_case.py  # 역사적 사례
    │   ├── portfolio.py    # 포트폴리오 (모의투자)
    │   ├── stock_listing.py    # 종목 목록
    │   ├── market_history.py   # 시장 히스토리
    │   ├── notification.py     # 알림
    │   ├── learning.py     # 학습 진도
    │   ├── reward.py       # 보상
    │   ├── report.py       # 증권사 리포트
    │   ├── glossary.py     # 용어사전
    │   └── tutor.py        # AI 튜터 세션
    ├── schemas/            # Pydantic v2 스키마
    │   ├── auth.py         # AuthRequest, AuthResponse
    │   ├── briefing.py     # BriefingResponse
    │   ├── case.py         # CaseResponse
    │   ├── narrative.py    # NarrativeResponse
    │   ├── portfolio.py    # PortfolioResponse
    │   ├── glossary.py     # GlossaryResponse
    │   ├── tutor.py        # TutorRequest, TutorResponse
    │   ├── pipeline.py     # PipelineResponse
    │   └── common.py       # 공용 스키마
    ├── api/routes/         # API 라우트 (각 파일이 APIRouter)
    │   ├── health.py       # GET /health
    │   ├── auth.py         # POST /auth/register, /auth/login, /auth/refresh
    │   ├── keywords.py     # GET /keywords/today
    │   ├── cases.py        # GET /cases/{id}
    │   ├── narrative.py    # GET /narrative/{id}
    │   ├── briefing.py     # GET /briefing/{date}
    │   ├── briefings.py    # GET /briefings (목록)
    │   ├── glossary.py     # GET /glossary/{term}
    │   ├── tutor.py        # POST /tutor/chat (SSE)
    │   ├── tutor_sessions.py  # 튜터 세션 관리
    │   ├── portfolio.py    # 포트폴리오 CRUD
    │   ├── trading.py      # 모의 매매
    │   ├── visualization.py   # 차트 데이터
    │   ├── highlight.py    # 용어 하이라이트
    │   ├── feedback.py     # 피드백
    │   ├── notification.py # 알림
    │   ├── pipeline.py     # 파이프라인 트리거
    │   ├── quiz_reward.py  # 퀴즈/보상
    │   ├── learning.py     # 학습 진도
    │   └── reports.py      # 증권사 리포트
    └── services/           # 비즈니스 로직
        ├── auth_service.py       # 인증 서비스
        ├── tutor_engine.py       # 튜터 엔진 (chatbot/ import)
        ├── portfolio_service.py  # 포트폴리오 서비스
        ├── narrative_builder.py  # 내러티브 조립
        ├── narrative_validator.py # 내러티브 검증
        ├── redis_cache.py        # Redis 캐시 매니저
        ├── llm_client.py         # LLM 클라이언트
        ├── code_executor.py      # 코드 실행 (차트)
        ├── chart_storage.py      # 차트 MinIO 저장
        ├── stock_resolver.py     # 종목 검색/해석
        ├── stock_price_service.py # 주가 서비스
        ├── kis_service.py        # 한국투자증권 API
        ├── market_calendar.py    # 시장 캘린더
        └── naver_report_service.py # 네이버 리포트
```

---

## 라우터 동적 등록

`app/main.py`에서 `importlib`을 사용해 라우터를 동적으로 로드한다.

```python
_route_modules = {}
for _mod_name in ["health", "auth", "briefing", ...]:
    try:
        _route_modules[_mod_name] = importlib.import_module(f"app.api.routes.{_mod_name}")
    except Exception as _e:
        _logging.getLogger("startup").warning(f"라우터 '{_mod_name}' 로드 실패 (무시): {_e}")
```

Docker 환경에서 일부 모듈이 없을 때도 graceful하게 처리된다. 로드 성공한 모듈만 `/api/v1` 프리픽스로 등록한다.

### 라우터 등록 규칙

| 설정 | 값 |
|------|-----|
| 프리픽스 | `/api/v1` (main.py에서 `include_router(..., prefix="/api/v1")`) |
| 라우터 파일 | `app/api/routes/{module}.py` |
| 라우터 변수 | `router = APIRouter(prefix="/{도메인}")` |
| 최종 경로 | `/api/v1/{도메인}/{endpoint}` |

---

## SQLAlchemy 패턴

### 모델 정의

```python
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class HistoricalCase(Base):
    __tablename__ = "historical_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    event_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(String)
    full_content: Mapped[str] = mapped_column(String)
    keywords: Mapped[dict] = mapped_column(JSON)  # JSONB
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

### 데이터베이스 세션

```python
from app.core.database import get_db

@router.get("/cases/{case_id}")
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HistoricalCase).where(HistoricalCase.id == case_id))
    case = result.scalar_one_or_none()
    ...
```

### 엔진 설정

```python
engine = create_async_engine(
    settings.DATABASE_URL,          # postgresql+asyncpg://...
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=50,
    max_overflow=100,
    pool_timeout=30,
    pool_recycle=1800,
)
```

---

## JWT 인증 (core/auth.py)

### 인증 의존성

| 함수 | 용도 |
|------|------|
| `get_current_user` | 필수 인증. 토큰 없으면 401. `{"id", "email", "username", "difficulty_level"}` 반환 |
| `get_current_user_optional` | 선택적 인증. 토큰 없으면 `None` 반환 |

### 사용 패턴

```python
from app.core.auth import get_current_user, get_current_user_optional

# 필수 인증 — user_id는 JWT에서 추출
@router.get("/portfolio")
async def get_portfolio(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user["id"]
    ...

# 선택적 인증 — 미인증 시 제한된 응답
@router.post("/tutor/chat")
async def tutor_chat(
    current_user: dict | None = Depends(get_current_user_optional),
    ...
):
    ...
```

### JWT 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `JWT_SECRET` | `narrative-invest-jwt-secret-change-in-production` | JWT 서명 키 |
| `JWT_ALGORITHM` | `HS256` | 알고리즘 |
| `JWT_EXPIRE_MINUTES` | `30` | 토큰 만료 시간 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 액세스 토큰 만료 |

---

## API 라우트 목록

| 라우터 | 경로 | 주요 엔드포인트 |
|--------|------|----------------|
| `health` | `/api/v1/health` | GET / — 헬스 체크 |
| `auth` | `/api/v1/auth` | POST /register, /login, /refresh |
| `keywords` | `/api/v1/keywords` | GET /today — 오늘의 키워드 |
| `cases` | `/api/v1/cases` | GET /{id} — 사례 상세 |
| `narrative` | `/api/v1/narrative` | GET /{id} — 내러티브 (6페이지 브리핑) |
| `briefing` | `/api/v1/briefing` | GET /{date} — 날짜별 브리핑 |
| `briefings` | `/api/v1/briefings` | GET / — 브리핑 목록 |
| `glossary` | `/api/v1/glossary` | GET /{term} — 용어 설명 |
| `tutor` | `/api/v1/tutor` | POST /chat — AI 튜터 (SSE 스트리밍) |
| `tutor_sessions` | `/api/v1/tutor_sessions` | 세션 CRUD |
| `portfolio` | `/api/v1/portfolio` | 포트폴리오 CRUD (JWT 인증) |
| `trading` | `/api/v1/trading` | 모의 매매 (JWT 인증) |
| `visualization` | `/api/v1/visualization` | 차트 데이터 |
| `highlight` | `/api/v1/highlight` | 용어 하이라이트 |
| `feedback` | `/api/v1/feedback` | 피드백 제출 |
| `notification` | `/api/v1/notification` | 알림 관리 (JWT 인증) |
| `pipeline` | `/api/v1/pipeline` | 파이프라인 트리거 |
| `quiz_reward` | `/api/v1/quiz_reward` | 퀴즈/보상 |
| `learning` | `/api/v1/learning` | 학습 진도 (JWT 인증) |
| `reports` | `/api/v1/reports` | 증권사 리포트 |

---

## 미들웨어

### CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # CORS_ALLOWED_ORIGINS에서 파싱
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 글로벌 레이트 리미팅

IP당 100 req/min, Redis INCR 패턴 사용. Redis 실패 시 rate limit 미적용 (graceful).

### 예외 처리

| 핸들러 | 대상 | 응답 |
|--------|------|------|
| `global_exception_handler` | 미처리 예외 | 500 + error_id (민감 정보 미노출) |
| `validation_exception_handler` | `RequestValidationError` | 422 + 구조화된 에러 |
| `_rate_limit_exceeded_handler` | `RateLimitExceeded` | 429 |

---

## Alembic 마이그레이션

### 디렉토리

```
database/
├── alembic.ini              # Alembic 설정
├── alembic/
│   ├── env.py               # 환경 설정 (DATABASE_URL 로드)
│   ├── script.py.mako       # 템플릿
│   └── versions/            # migration 파일들
└── scripts/
    ├── create_database.py   # DB 초기 생성
    ├── reset_db.py          # DB 리셋 (--content-only 옵션)
    └── init_stock_listings.py  # 종목 목록 초기화
```

### 명령어

| 작업 | 로컬 | Docker |
|------|------|--------|
| migration 생성 | `cd database && ../.venv/bin/alembic revision --autogenerate -m "설명"` | - |
| migration 적용 | `cd database && ../.venv/bin/alembic upgrade head` | `docker compose -f docker-compose.dev.yml run db-migrate` |
| 현재 상태 확인 | `cd database && ../.venv/bin/alembic current` | - |
| 히스토리 확인 | `cd database && ../.venv/bin/alembic history` | - |
| deploy-test 적용 | - | `ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'` |

### 주의사항

- migration 생성 시 반드시 diff를 확인하여 불필요한 변경(예: 기존 테이블 재생성)이 포함되지 않았는지 검증
- `asyncpg` 드라이버 URL은 Alembic env.py에서 동기 드라이버(`psycopg2`)로 자동 변환
- migration 파일은 반드시 PR에 포함하여 리뷰 대상으로 포함

---

## Chatbot 연동

`fastapi/app/services/tutor_engine.py`에서 `chatbot/` 모듈을 직접 import한다.

```python
from chatbot.agent.tutor_agent import create_tutor_agent
```

Chatbot의 `agent/tutor_agent.py` 시그니처가 변경되면 `tutor_engine.py`도 수정해야 한다.

---

## Redis 캐시

`app/services/redis_cache.py`에서 Redis 클라이언트를 관리한다.

| 용도 | TTL | 키 패턴 |
|------|-----|---------|
| 브리핑 캐시 | 6시간 | `briefing:{date}` |
| Rate Limiting | 60초 | `rate_limit:{ip}` |
| 용어 캐시 | 24시간 | `glossary:{term}` |

---

## 설정 (core/config.py)

`pydantic-settings`의 `BaseSettings`로 환경변수를 관리한다. `.env` 파일 경로는 프로젝트 루트의 `.env`를 자동 참조한다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...localhost:5432/narrative_investment` | DB 연결 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 연결 |
| `JWT_SECRET` | (변경 필수) | JWT 서명 키 |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,...` | CORS 허용 목록 |
| `DEBUG` | `false` | 디버그 모드 |
