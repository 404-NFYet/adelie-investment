# Backend 교차 의존성

> Backend 변경이 다른 파트에 미치는 영향과, 다른 파트 변경 시 Backend에 미치는 영향을 정리한다.

---

## 1. DB 스키마 변경 체크리스트

Backend에서 SQLAlchemy 모델(`app/models/`)을 수정할 때 확인해야 할 사항.

### 변경 전

- [ ] 어떤 테이블/컬럼이 변경되는지 목록 작성
- [ ] 해당 테이블을 사용하는 파트 확인 (아래 매트릭스 참조)

### 변경 후

- [ ] Alembic migration 생성
  ```bash
  cd database && ../.venv/bin/alembic revision --autogenerate -m "설명"
  ```
- [ ] migration 파일 diff 확인 (불필요한 변경 없는지)
- [ ] 로컬에서 migration 적용 + 테스트
  ```bash
  cd database && ../.venv/bin/alembic upgrade head
  ```
- [ ] 관련 스키마(`app/schemas/`) 업데이트
- [ ] 관련 라우트(`app/api/routes/`) 업데이트

### 파이프라인 영향 확인

- [ ] `datapipeline/db/writer.py`에서 해당 테이블 사용 여부 확인
- [ ] 컬럼 추가: NOT NULL + DEFAULT 없으면 writer.py 수정 필수
- [ ] 컬럼 삭제/리네임: writer.py의 INSERT/UPDATE 쿼리 수정 필수
- [ ] JSONB 구조 변경: `_build_top_keywords()`, `_build_case_keywords()` 확인

### 프론트엔드 영향 확인

- [ ] API 응답 구조가 변경되는 라우트 목록 작성
- [ ] 해당 라우트를 호출하는 `frontend/src/api/*.js` 파일 확인
- [ ] PR에 `[영향: Frontend, Pipeline]` 태그 + 담당자 리뷰어 추가

### 테이블별 사용 파트 매트릭스

| 테이블 | Backend (route) | Pipeline (writer.py) | Frontend (API) |
|--------|----------------|---------------------|----------------|
| `daily_briefings` | keywords, briefing, briefings | UPSERT | Home.jsx |
| `briefing_stocks` | keywords, briefing | INSERT | Home.jsx |
| `historical_cases` | cases, narrative, story | INSERT | Narrative.jsx, Story.jsx |
| `case_matches` | cases, comparison | INSERT | Comparison.jsx |
| `case_stock_relations` | cases, companies | INSERT | Companies.jsx |
| `users` | auth | - | Auth.jsx, Profile.jsx |
| `portfolios` | portfolio, trading | - | Portfolio.jsx |
| `tutor_sessions` | tutor_sessions | - | TutorChat.jsx |
| `notifications` | notification | - | Notifications.jsx |
| `learning_progress` | learning | - | Profile.jsx |
| `rewards` | quiz_reward | - | Portfolio.jsx |
| `stock_listings` | trading | - | Portfolio.jsx |
| `glossary_items` | glossary, highlight | - | TermBottomSheet.jsx |

---

## 2. Chatbot agent 시그니처 변경

`fastapi/app/services/tutor_engine.py`에서 `chatbot/` 모듈을 직접 import한다.

### 연동 파일

```
chatbot/agent/tutor_agent.py    (에이전트 정의)
    ↓ import
fastapi/app/services/tutor_engine.py  (엔진 래퍼)
    ↓ 호출
fastapi/app/api/routes/tutor.py       (SSE 스트리밍 라우트)
```

### 체크리스트

Chatbot 담당자(정지훈)가 에이전트 인터페이스를 변경할 때:

- [ ] `tutor_agent.py`의 함수 시그니처 (인자, 반환값) 변경 여부 확인
- [ ] `tutor_engine.py`에서 호출 방식 수정
- [ ] SSE 이벤트 타입/형식 변경 시 Frontend 담당자(손영진)에게도 알림

### SSE 이벤트 형식 (현재)

```
event: step        → {type: "thinking" | "tool_call", content: "..."}
event: text_delta  → {content: "..."}
event: sources     → {type: "sources", sources: [...]}
event: visualization → {type: "visualization", data: {...}}
event: done        → {session_id: "...", total_tokens: N}
event: error       → {type: "error", error: "..."}
```

---

## 3. API 스키마 변경 (Backend → Frontend)

### 체크리스트

Backend에서 API 응답/요청 스키마(`app/schemas/`)를 변경할 때:

- [ ] Swagger UI(`/docs`) 캡처를 Discord #backend 채널에 공유
- [ ] `frontend/src/api/*.js`에서 해당 엔드포인트 호출부 확인
  - `client.js` — `fetchJson`, `postJson`, `deleteJson`
  - `index.js` — `casesApi`, `keywordsApi`, `notificationApi`
  - `auth.js` — `authApi`
  - `narrative.js` — `narrativeApi`
  - `portfolio.js` — `portfolioApi`
- [ ] Frontend 페이지/컴포넌트에서 응답 데이터 참조 부분 확인
- [ ] PR에 `[영향: Frontend]` 태그 + 손영진 리뷰어 추가

### 주요 API → Frontend 매핑

| API 엔드포인트 | Frontend API 파일 | Frontend 페이지 |
|---------------|-------------------|----------------|
| `GET /api/v1/keywords/today` | `src/api/index.js` | `Home.jsx` |
| `GET /api/v1/cases/{id}` | `src/api/index.js` | `Matching.jsx` |
| `GET /api/v1/narrative/{id}` | `src/api/narrative.js` | `Narrative.jsx` |
| `POST /api/v1/auth/login` | `src/api/auth.js` | `Auth.jsx` |
| `GET /api/v1/portfolio` | `src/api/portfolio.js` | `Portfolio.jsx` |
| `POST /api/v1/tutor/chat` | (SSE 직접 호출) | `TutorPanel.jsx` |

---

## 4. 환경변수 변경 시

### Backend가 관리하는 핵심 환경변수

| 변수 | 영향 범위 |
|------|----------|
| `DATABASE_URL` | Backend + Pipeline (writer.py) |
| `REDIS_URL` | Backend 캐시/Rate Limiting |
| `JWT_SECRET` | Backend 인증 (변경 시 모든 토큰 무효화) |
| `CORS_ALLOWED_ORIGINS` | Frontend 접근 제어 |
| `OPENAI_API_KEY` | Backend LLM + Pipeline |

### 체크리스트

- [ ] `.env.example` 업데이트
- [ ] `docker-compose.dev.yml`, `docker-compose.prod.yml`의 `environment` 섹션 확인
- [ ] Pipeline `datapipeline/config.py`에서 동일 변수를 참조하는지 확인
- [ ] Infra 담당자(도형준)에게 deploy-test `.env` 동기화 요청

---

## 5. Backend가 영향 받는 외부 변경

| 변경 주체 | 변경 내용 | Backend 확인 사항 |
|-----------|----------|------------------|
| Infra | docker-compose 포트/서비스명 변경 | `DATABASE_URL`, `REDIS_URL` 환경변수 확인 |
| Infra | 환경변수 추가/삭제 | `app/core/config.py` Settings 클래스 확인 |
| Pipeline | writer.py JSONB 구조 변경 | 관련 API route 응답 검증 |
| Pipeline | schemas.py 변경 | Backend schemas와 불일치 여부 확인 |
| Chatbot | agent 시그니처 변경 | `tutor_engine.py` import/호출 수정 |
| Frontend | 새 페이지/기능 추가 | 필요한 API 엔드포인트 구현 |
