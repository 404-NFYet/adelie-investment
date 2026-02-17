# 백엔드 개발 가이드 — 허진서

## 환경 정보
- LXD 컨테이너: `ssh dev-jjjh02`
- Git 설정: user.name=jjjh02, user.email=jinnyshur0104@gmail.com
- 브랜치: `dev/backend`

## 개발 시작

### Docker 환경 (권장)
```bash
make dev-api
# 또는
docker compose -f docker-compose.dev.yml up backend-api postgres redis
```
- URL: http://localhost:8082
- Swagger UI: http://localhost:8082/docs
- FastAPI auto-reload 활성화 (코드 수정 시 자동 재시작)

### 로컬 환경 (Docker 없이)
```bash
cd fastapi
source ../.venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```
- `.env`의 `DATABASE_URL`, `REDIS_URL` 확인 필요
- PostgreSQL, Redis가 로컬 또는 원격에서 실행 중이어야 함

## 담당 디렉토리

```
fastapi/
├── app/
│   ├── main.py                  # FastAPI app 생성, 라우터 동적 로딩
│   ├── models/                  # SQLAlchemy ORM 모델
│   │   ├── user.py
│   │   ├── keyword.py
│   │   ├── case.py
│   │   ├── portfolio.py
│   │   └── ...
│   ├── schemas/                 # Pydantic 스키마 (request/response)
│   │   ├── user.py
│   │   ├── keyword.py
│   │   └── ...
│   ├── api/routes/              # API 엔드포인트 라우터
│   │   ├── auth.py              # /api/v1/auth/*
│   │   ├── keywords.py          # /api/v1/keywords/*
│   │   ├── cases.py             # /api/v1/cases/*
│   │   ├── portfolio.py         # /api/v1/portfolio/*
│   │   ├── tutor.py             # /api/v1/tutor/*
│   │   └── ...
│   ├── services/                # 비즈니스 로직
│   │   ├── auth_service.py      # JWT 토큰 생성/검증
│   │   ├── keyword_service.py
│   │   └── ...
│   ├── core/                    # 공통 설정, 유틸리티
│   │   ├── config.py            # pydantic-settings 기반 환경변수
│   │   ├── database.py          # async SQLAlchemy engine, Base
│   │   ├── security.py          # password hashing, JWT
│   │   └── dependencies.py      # get_current_user, get_db 등
│   └── utils/                   # 헬퍼 함수
└── requirements.txt

database/
├── alembic/                     # DB 마이그레이션
│   ├── versions/                # 마이그레이션 버전 파일
│   └── env.py
├── alembic.ini                  # Alembic 설정
└── scripts/                     # DB 관리 스크립트
    ├── reset_db.py
    ├── create_database.py
    └── init_stock_listings.py
```

### 핵심 파일
- `app/main.py`: 라우터 자동 등록 (importlib), CORS 설정, lifespan event
- `app/core/database.py`: AsyncEngine, async_sessionmaker, Base
- `app/core/dependencies.py`: `get_current_user` (JWT 검증), `get_db` (세션 관리)
- `database/alembic/env.py`: Alembic 비동기 마이그레이션 설정

## 개발 워크플로우

1. **새 API 엔드포인트 추가**
   ```bash
   # 1. models/ 에 ORM 모델 정의
   # 2. schemas/ 에 Pydantic 스키마 정의
   # 3. api/routes/ 에 라우터 생성
   # 4. services/ 에 비즈니스 로직 작성 (선택)
   # 5. main.py는 자동으로 라우터 로드 (수동 등록 불필요)
   ```

2. **DB 마이그레이션 생성**
   ```bash
   # 로컬 가상환경
   cd database
   ../.venv/bin/alembic revision --autogenerate -m "Add new_table"
   ../.venv/bin/alembic upgrade head

   # Docker 환경
   docker compose -f docker-compose.dev.yml run db-migrate
   ```

3. **인증 패턴**
   - JWT 필수: `current_user: User = Depends(get_current_user)`
   - JWT 선택: `current_user: Optional[User] = Depends(get_current_user_optional)`
   - user_id는 경로 파라미터가 아닌 JWT에서 추출: `current_user.id`

4. **DB 쿼리**
   ```python
   from app.core.dependencies import get_db
   from sqlalchemy.ext.asyncio import AsyncSession

   async def get_items(db: AsyncSession = Depends(get_db)):
       result = await db.execute(select(Item).where(Item.user_id == user_id))
       return result.scalars().all()
   ```

## 테스트

### Unit 테스트
```bash
make test
# 또는
docker compose -f docker-compose.test.yml run --rm backend-test

# 로컬 실행
source .venv/bin/activate
pytest tests/unit/ -v
pytest tests/unit/test_auth.py::test_login -v
```
- 테스트 파일: `tests/unit/`, `tests/backend/`
- `pytest.ini`에서 `asyncio_mode = auto` 설정됨

### API 테스트 (수동)
```bash
# Swagger UI 사용
open http://localhost:8082/docs

# curl 테스트
curl http://localhost:8082/api/v1/keywords/today
```

## 다른 파트와의 연동

### Frontend (손영진)
- **영향주는 경우**: API 엔드포인트 추가/변경, response 스키마 변경
- **알림 필요**: Swagger UI 스크린샷 또는 스키마 공유
- **주의**:
  - response 필드명 변경 → Frontend `src/api/*.js` 수정 필요
  - 인증 방식 변경 → `client.js`의 Authorization 헤더 로직 확인

### Chatbot (정지훈)
- **영향주는 경우**: DB 모델 변경 (chatbot이 참조하는 테이블), tutor API 변경
- **알림 필요**: `app/models/` 변경 시 마이그레이션 공유
- **주의**: chatbot에서 FastAPI DB 세션을 공유하므로 모델 일관성 유지

### Pipeline (안례진)
- **영향주는 경우**: DB 스키마 변경 (keywords, cases, narratives, glossary 등)
- **알림 필요**: Alembic migration 파일 공유, `datapipeline/db/writer.py` 수정 필요 여부
- **주의**:
  - Pipeline은 asyncpg로 직접 DB 접속 → SQLAlchemy 모델과 스키마 일치 확인
  - 날짜 컬럼 타입 변경 시 KST 처리 로직 점검

### Infra (도형준)
- **영향받는 경우**: Docker 이미지 재빌드, 환경변수 추가, DB 마이그레이션
- **협업 필요**:
  - `.env.example` 업데이트
  - `docker-compose.*.yml`에 환경변수 추가
  - deploy-test 배포 전 마이그레이션 실행 확인
- **주의**: Alembic migration은 배포 직전에 실행 (롤백 계획 필요)

## 커밋 전 체크리스트
- [ ] `git config user.name` = jjjh02
- [ ] `git config user.email` = jinnyshur0104@gmail.com
- [ ] 새 API는 Swagger UI에서 테스트 완료
- [ ] DB 모델 변경 시 Alembic migration 생성
- [ ] pytest 테스트 통과 (`make test`)
- [ ] `.env.example`에 새 환경변수 추가 (있다면)
- [ ] 커밋 메시지 형식: `feat: 포트폴리오 조회 API 추가` (한글, type prefix)
