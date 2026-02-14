# Data Pipeline 교차 의존성

> 다른 파트 변경이 파이프라인에 미치는 영향과 대응법을 정리한다.

---

## 1. Backend DB 모델 변경 시

파이프라인은 `datapipeline/db/writer.py`에서 asyncpg로 **직접 SQL을 실행**한다.
Backend의 SQLAlchemy 모델(`fastapi/app/models/`)과 직접 의존하지 않지만, **동일한 DB 테이블을 대상**으로 한다.

### 영향 받는 테이블

| 테이블 | writer.py 사용 방식 |
|--------|---------------------|
| `daily_briefings` | UPSERT (briefing_date 기준) |
| `briefing_stocks` | INSERT (ON CONFLICT DO NOTHING) |
| `historical_cases` | INSERT (keywords JSONB) |
| `case_matches` | INSERT |
| `case_stock_relations` | INSERT |

### 체크리스트

Backend에서 위 테이블의 컬럼을 **추가/삭제/타입 변경**할 때:

- [ ] `datapipeline/db/writer.py`의 INSERT/UPDATE 쿼리 확인
  - 컬럼명, 타입, NOT NULL 제약 조건 일치 여부
- [ ] `datapipeline/schemas.py`의 Pydantic 스키마 동기화
  - writer가 schemas.py의 `FullBriefingOutput` 구조에서 데이터를 추출
- [ ] Alembic migration 적용 후 파이프라인 mock 테스트 재실행
  - `.venv/bin/python -m datapipeline.run --backend mock`
- [ ] deploy-test에서 migration 적용 후 live 테스트
  - `.venv/bin/python -m datapipeline.run --backend live --topic-count 1`

### 예시: `daily_briefings`에 컬럼 추가

```
1. Backend: app/models/briefing.py에 컬럼 추가
2. Backend: Alembic migration 생성 + 적용
3. Pipeline: writer.py의 INSERT/UPDATE에 새 컬럼 반영
4. Pipeline: mock 테스트 → live 테스트
```

---

## 2. 환경변수 변경 시

파이프라인은 `datapipeline/config.py`에서 프로젝트 루트 `.env`를 로드한다.

### 영향 받는 환경변수

| 변수 | 사용처 |
|------|--------|
| `OPENAI_API_KEY` | multi_provider_client.py |
| `PERPLEXITY_API_KEY` | multi_provider_client.py |
| `CLAUDE_API_KEY` | multi_provider_client.py (Anthropic) |
| `DATABASE_URL` | db/writer.py |
| `DEFAULT_MODEL` | config.py → 내러티브 생성 모델 |
| `CHART_MODEL` | config.py → 차트 생성 모델 |

### 체크리스트

Infra 또는 Backend에서 환경변수를 **추가/변경/삭제**할 때:

- [ ] `datapipeline/config.py`에서 해당 변수를 참조하는지 확인
- [ ] `.env.example` 업데이트 확인
- [ ] Docker 환경 (`docker-compose.dev.yml`, `docker-compose.prod.yml`)의 `env_file` 또는 `environment` 섹션 확인
- [ ] 로컬 `.env`와 deploy-test `.env` 동기화

---

## 3. DB 스키마 변경 (Alembic)

### 영향 경로

```
database/alembic/versions/   (migration 파일)
    ↓ alembic upgrade head
fastapi/app/models/           (SQLAlchemy 모델 — Backend가 관리)
    ↓ 테이블 구조 변경
datapipeline/db/writer.py     (asyncpg 직접 SQL)
```

### 체크리스트

- [ ] migration 파일에서 파이프라인이 사용하는 테이블 변경 여부 확인
  - `daily_briefings`, `briefing_stocks`, `historical_cases`, `case_matches`, `case_stock_relations`
- [ ] 컬럼 추가: writer.py에서 새 컬럼에 값을 넣어야 하는지 확인
  - NOT NULL + DEFAULT 없는 컬럼이면 writer.py 수정 필수
- [ ] 컬럼 삭제/리네임: writer.py의 쿼리가 깨지지 않는지 확인
- [ ] JSONB 구조 변경: `_build_top_keywords()`, `_build_case_keywords()` 출력 구조가 Backend API 응답과 일치하는지 확인

---

## 4. API 스키마 변경 (Backend → Frontend)

파이프라인이 DB에 저장하는 JSONB 구조는 Backend API 응답에 그대로 포함된다.

### 데이터 흐름

```
datapipeline/db/writer.py
    ↓ daily_briefings.top_keywords (JSONB)
fastapi/app/api/routes/keywords.py
    ↓ GET /api/v1/keywords/today
frontend/src/pages/Home.jsx

datapipeline/db/writer.py
    ↓ historical_cases.keywords (JSONB)
fastapi/app/api/routes/narrative.py
    ↓ GET /api/v1/narrative/{id}
frontend/src/pages/Narrative.jsx
```

### 체크리스트

Backend에서 API 응답 스키마를 변경할 때:

- [ ] writer.py의 JSONB 빌드 함수가 새 스키마와 호환되는지 확인
  - `_build_top_keywords()` → `GET /api/v1/keywords/today` 응답 구조
  - `_build_case_keywords()` → `GET /api/v1/narrative/{id}` 응답 구조
- [ ] 파이프라인 mock 실행 → DB 저장 → API 호출 → 응답 검증

---

## 5. 파이프라인이 다른 파트에 미치는 영향

파이프라인 출력 구조를 변경할 때 확인해야 할 사항:

| 변경 항목 | 영향 대상 | 확인 파일 |
|-----------|----------|----------|
| `_build_top_keywords()` 출력 변경 | Frontend Home.jsx | `src/api/index.js`, `src/pages/Home.jsx` |
| `_build_case_keywords()` 출력 변경 | Frontend Narrative.jsx, Story.jsx | `src/api/narrative.js`, `src/pages/Narrative.jsx` |
| `_build_full_content()` 출력 변경 | Backend narrative route | `fastapi/app/api/routes/narrative.py` |
| `schemas.py` 구조 변경 | writer.py, 테스트 | `db/writer.py`, `tests/test_schemas.py` |

### PR 작성 시

파이프라인 출력 구조를 변경하는 PR에는 반드시 `[영향: Backend, Frontend]` 태그를 포함하고, 관련 담당자(허진서, 손영진)를 리뷰어로 추가한다.
