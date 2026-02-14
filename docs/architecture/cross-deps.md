# 교차 의존성 매트릭스

> 각 파트 변경 시 다른 파트에 미치는 영향을 정리한 문서.
> PR 작성 전 반드시 확인하여 영향 범위를 파악한다.

## 담당자

| 파트 | 담당자 | 주요 디렉토리 |
|------|--------|--------------|
| Frontend | 손영진 | `frontend/` |
| Backend | 허진서 | `fastapi/` |
| Chatbot | 정지훈 | `chatbot/` |
| Pipeline | 안례진 | `datapipeline/` |
| Infra | 도형준 | `lxd/`, `docker-compose.*`, `Makefile`, `.github/` |
| Database | 허진서 + 도형준 | `database/` (Alembic migrations) |

---

## 1. 5x5 교차 의존성 매트릭스

행: **변경하는 파트**, 열: **영향 받는 파트**

| 변경 \ 영향 | Frontend | Backend | Chatbot | Pipeline | Infra |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Frontend** | - | 새 페이지 추가 시 Backend API 필요 여부 확인 | 튜터 UI (`components/tutor/`) 변경 시 SSE 이벤트 형식 확인 | 영향 없음 | nginx 라우트 추가 필요 시 `frontend/nginx.conf` 수정 |
| **Backend** | API 스키마 변경 시 `src/api/*` 수정 필요 | - | `tutor_engine.py`가 `chatbot/` 모듈 직접 import — chatbot 인터페이스 변경 시 동기화 필요 | DB 모델 변경 시 `datapipeline/db/writer.py` 쿼리 확인 | `fastapi/Dockerfile` 변경 시 `docker-compose.*.yml` 빌드 컨텍스트 확인 |
| **Chatbot** | SSE 이벤트 형식/프롬프트 변경 시 `components/tutor/MessageBubble.jsx` 등 수정 가능 | `agent/tutor_agent.py` 시그니처 변경 시 `fastapi/app/services/tutor_engine.py` 수정 필요 | - | 영향 없음 | `chatbot/requirements.txt` 변경 시 `fastapi/Dockerfile`에 반영 (같은 이미지에 포함) |
| **Pipeline** | 출력 구조 변경 시 `src/api/narrative.js`, `pages/Narrative.jsx` 등 수정 가능 | `db/writer.py` 저장 구조 변경 시 Backend routes (`keywords`, `cases`, `narrative`, `briefing`) 응답 형식 확인 | 영향 없음 | - | `datapipeline/Dockerfile` 변경 시 `docker-compose.*.yml` ai-pipeline 서비스 확인 |
| **Infra** | `docker-compose.*.yml` 포트/서비스명 변경 시 Frontend 프록시 설정 확인 | 환경변수/서비스명 변경 시 Backend `.env` 및 설정 확인 | 영향 없음 (Backend 이미지에 포함) | 환경변수 변경 시 `datapipeline/config.py` 확인 | - |

---

## 2. 파트별 변경 시 확인 체크리스트

### Backend API 스키마 변경

Backend에서 API 응답/요청 스키마(`app/schemas/`)를 수정할 때:

- [ ] Swagger UI(`/docs`) 캡처 또는 링크를 Discord에 공유
- [ ] Frontend `src/api/*.js` 파일에서 해당 엔드포인트 호출부 수정
- [ ] Frontend 페이지/컴포넌트에서 응답 데이터 구조 참조하는 부분 수정
- [ ] PR 설명에 `[영향: Frontend]` 태그 포함

**영향 파일 예시:**

```
# Backend 변경 파일
fastapi/app/schemas/briefing.py
fastapi/app/api/routes/briefing.py

# Frontend 수정 필요 파일
frontend/src/api/index.js          (엔드포인트 URL)
frontend/src/api/narrative.js      (응답 파싱)
frontend/src/pages/Home.jsx        (데이터 바인딩)
```

### Backend DB 모델 변경

Backend에서 SQLAlchemy 모델(`app/models/`)을 수정할 때:

- [ ] Alembic migration 생성: `cd database && alembic revision --autogenerate -m "설명"`
- [ ] migration 파일 리뷰 (불필요한 변경 없는지 확인)
- [ ] Pipeline `datapipeline/db/writer.py`에서 해당 테이블 INSERT/UPDATE 쿼리 확인
- [ ] deploy-test 서버에 migration 적용: `ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'`
- [ ] PR 설명에 `[영향: Database, Pipeline]` 태그 포함

**영향 파일 예시:**

```
# Backend 변경 파일
fastapi/app/models/briefing.py

# Migration 생성
database/alembic/versions/xxxx_설명.py

# Pipeline 확인 필요 파일
datapipeline/db/writer.py          (INSERT/UPDATE 쿼리)
datapipeline/schemas.py            (Pydantic 스키마)
```

### Chatbot 프롬프트/SSE 변경

Chatbot에서 프롬프트 또는 SSE 스트리밍 형식을 변경할 때:

- [ ] `fastapi/app/services/tutor_engine.py`에서 chatbot import 경로 및 함수 시그니처 확인
- [ ] Frontend `components/tutor/MessageBubble.jsx`에서 SSE 이벤트 파싱 확인
- [ ] Frontend `components/tutor/TutorPanel.jsx`에서 스트리밍 처리 확인
- [ ] SSE 이벤트 타입 변경 시: `text_delta`, `step`, `sources`, `visualization`, `done`, `error`
- [ ] PR 설명에 `[영향: Frontend, Backend]` 태그 포함

**SSE 이벤트 형식 (현재 기준):**

```
event: step        → {type: "thinking", content: "..."} 또는 {type: "tool_call", ...}
event: text_delta  → {content: "..."}
event: sources     → {type: "sources", sources: [...]}
event: done        → {session_id: "...", total_tokens: N}
event: error       → {type: "error", error: "..."}
```

### Pipeline 출력 구조 변경

Pipeline에서 `datapipeline/db/writer.py` 또는 `datapipeline/schemas.py`의 출력 구조를 변경할 때:

- [ ] Backend routes 확인: `keywords.py`, `cases.py`, `narrative.py`, `briefing.py`, `briefings.py`
- [ ] `datapipeline/db/writer.py`의 `_build_top_keywords()`, `_build_case_keywords()` 출력 구조가 API 응답과 일치하는지 확인
- [ ] Frontend 페이지 확인: `Home.jsx` (키워드 카드), `Narrative.jsx` (내러티브), `Comparison.jsx`, `Story.jsx`
- [ ] PR 설명에 `[영향: Backend, Frontend]` 태그 포함

**데이터 흐름:**

```
datapipeline/db/writer.py → DB 테이블
  → daily_briefings.top_keywords (JSON)  → GET /api/v1/keywords/today   → Home.jsx
  → historical_cases.keywords (JSON)     → GET /api/v1/story/{id}       → Story.jsx
  → historical_cases.full_content        → GET /api/v1/narrative/{id}    → Narrative.jsx
  → case_matches                         → GET /api/v1/comparison/{id}   → Comparison.jsx
```

### Frontend 새 페이지 추가

Frontend에서 새 페이지를 추가할 때:

- [ ] Backend에 필요한 API 엔드포인트가 있는지 확인 (없으면 Backend 담당자와 협의)
- [ ] `src/pages/NewPage.jsx` 생성 + `default export`
- [ ] `App.jsx`에 `React.lazy` + `<Route>` 추가
- [ ] 필요 시 `src/api/` 에 API 호출 함수 추가
- [ ] 인증 필요 페이지는 `<ProtectedRoute>`로 감싸기
- [ ] PR 설명에 `[영향: Backend (API 필요 시)]` 태그 포함

### Infra docker-compose 변경

Infra에서 `docker-compose.*.yml` 또는 `Makefile`을 변경할 때:

- [ ] 모든 팀원에게 Discord 공지
- [ ] 환경변수 추가/변경 시 `.env.example` 업데이트
- [ ] 서비스 포트 변경 시 Frontend `vite.config.js` proxy 설정 확인
- [ ] 서비스명 변경 시 `docker-compose.dev.yml`, `docker-compose.prod.yml`, `docker-compose.test.yml` 모두 동기화
- [ ] 변경 후 팀원들이 `docker compose pull` 필요한지 안내
- [ ] PR 설명에 `[영향: 전체]` 태그 포함

---

## 3. 의사소통 규칙

### PR 규칙

1. **PR 제목에 영향 파트 표기**: 다른 파트에 영향이 있으면 `[영향: Frontend, Pipeline]` 형태로 표기
2. **PR 리뷰어에 영향 파트 담당자 추가**: 영향 받는 파트 담당자를 반드시 리뷰어로 지정
3. **Breaking Change는 즉시 Discord 공유**: API 스키마, DB 스키마, SSE 형식 변경 등

### Discord 공유 항목

| 변경 유형 | 공유 채널 | 공유 내용 |
|-----------|----------|----------|
| API 스키마 변경 | #backend | Swagger UI 링크 + 변경 필드 설명 |
| DB 스키마 변경 | #backend | migration 파일명 + 변경 테이블/컬럼 |
| SSE 이벤트 변경 | #frontend | 이벤트 타입 + 데이터 구조 예시 |
| Pipeline 출력 변경 | #data | 변경 전/후 JSON 구조 비교 |
| 환경변수 추가/변경 | #infra | `.env.example` diff + 설정 방법 |
| docker-compose 변경 | #infra | 재시작 명령어 안내 |

### 동기화 타이밍

- **API 변경**: Backend PR 머지 전에 Frontend PR 준비 (동시 머지 권장)
- **DB 변경**: migration 먼저 적용 → Backend 코드 배포 → Pipeline 코드 배포
- **Infra 변경**: Discord 공지 → 팀원 확인 → 머지 및 배포
