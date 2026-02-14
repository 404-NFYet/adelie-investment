# Chatbot 교차 의존성

챗봇이 다른 파트의 변경에 영향을 받는 지점과 대응 방법을 정리한다.

## 1. tutor_engine (FastAPI 서비스)

### 의존 관계
- 프로덕션 튜터 엔진은 `fastapi/app/services/tutor_engine.py`에 위치
- `chatbot/tools/visualization_tool.py`를 `sys.path.insert`로 임포트
- `chatbot/prompts/templates/`의 프롬프트 템플릿을 참조할 수 있음

### 영향 받는 변경
| FastAPI 변경 | 챗봇 대응 |
|-------------|----------|
| `tutor_engine.py` 로직 변경 | 프롬프트/도구 호출 방식 확인 |
| `TutorSession`/`TutorMessage` 모델 변경 | 세션 저장/조회 로직 확인 |
| `TutorChatRequest` 스키마 변경 | 요청 파라미터 변경 반영 |
| 라우트 경로 변경 (`tutor.py`) | 프론트엔드에 공유 (챗봇 자체 영향 없음) |
| 의존성 주입 변경 (`get_db`, `get_current_user`) | `tutor_engine.py`의 파라미터 확인 |

### 확인 방법
```bash
# tutor_engine이 chatbot 모듈을 어떻게 임포트하는지 확인
grep -n "chatbot" fastapi/app/services/tutor_engine.py

# 관련 모델/스키마 확인
cat fastapi/app/models/tutor.py
cat fastapi/app/schemas/tutor.py
```

## 2. 튜터 UI (Frontend)

### 의존 관계
- 프론트엔드의 `TutorContext.jsx`가 SSE 연결을 관리
- `components/tutor/`에서 스트리밍 메시지를 실시간 렌더링
- `ChatFAB`(전역 FAB 버튼)과 `TutorModal`이 튜터 진입점

### 영향 받는 변경
| 프론트 변경 | 챗봇 대응 |
|------------|----------|
| SSE 파싱 로직 변경 | SSE 이벤트 포맷과 일치하는지 확인 |
| 새 UI 기능 (난이도 선택, 대화 내보내기 등) | 백엔드 API 추가 필요 여부 판단 |
| TutorContext 상태 구조 변경 | 직접 영향 없음 (API 계약만 유지하면 됨) |
| 차트 렌더링 컴포넌트 변경 | `visualization_tool.py`의 출력 포맷 확인 |

### SSE 이벤트 계약
프론트엔드와 합의된 SSE 이벤트 포맷. 변경 시 양측 동시 배포 필요.
```
event: content   → data: {"token": "텍스트"}
event: chart     → data: {"chart_url": "...", "title": "..."}
event: done      → data: {"session_id": "...", "message_id": "..."}
event: error     → data: {"message": "에러 내용"}
```

## 3. Data Pipeline 출력

### 의존 관계
- 파이프라인이 DB에 저장한 데이터를 도구(tools)가 조회
- `briefing_tool.py` → 오늘의 브리핑/키워드 데이터
- `search_tool.py` → 히스토리컬 케이스 데이터
- `comparison_tool.py` → 과거-현재 비교 데이터
- `glossary_tool.py` → 용어 사전 데이터

### 영향 받는 변경
| 파이프라인 변경 | 챗봇 대응 |
|----------------|----------|
| DB 테이블 스키마 변경 | 해당 도구의 DB 쿼리 수정 |
| 새 데이터 유형 추가 | 새 도구 개발 또는 기존 도구 확장 |
| 내러티브 포맷 변경 | 컨텍스트 주입 로직 수정 (`tutor_engine.py`) |
| 용어 사전 구조 변경 | `glossary_tool.py` + `term_highlighter.py` 수정 |

### 데이터 테이블 참조
| 도구 | 참조 테이블 | 모델 |
|------|-----------|------|
| briefing_tool | `keywords`, `daily_briefings` | `app.models` |
| search_tool | `historical_cases` | `HistoricalCase` |
| glossary_tool | `glossaries` | `Glossary` |
| comparison_tool | `historical_cases`, `keywords` | — |
| visualization_tool | 외부 API (주가 데이터) | — |

## 4. 환경변수

### 챗봇 관련 환경변수
| 변수 | 용도 | 필수 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API (튜터 LLM + 시각화) | 필수 |
| `PERPLEXITY_API_KEY` | Perplexity API (검색 도구) | 선택 |
| `LANGCHAIN_API_KEY` | LangSmith 트레이싱 | 선택 |
| `CLAUDE_API_KEY` | Claude API (시각화 도구 대안) | 선택 |
| `DATABASE_URL` | PostgreSQL (세션 저장, 데이터 조회) | 필수 |
| `REDIS_URL` | Redis (캐시) | 필수 |

> 모든 환경변수는 프로젝트 루트의 `.env`에서 로드한다. 챗봇 모듈 전용 `.env`는 없다.

## 5. 변경 대응 프로세스

1. **DB 스키마 변경 시** — 백엔드 담당자가 Alembic 마이그레이션 후 챗봇 도구 영향 확인 요청
2. **SSE 포맷 변경 시** — 챗봇 담당자가 프론트 담당자에게 사전 공유, 양측 동시 배포
3. **프롬프트 변경 시** — `chatbot/prompts/templates/`에서 수정, 변경 사유를 커밋 메시지에 명시
4. **도구 추가/변경 시** — `tutor_engine.py`에서 임포트 경로 확인, Docker 빌드 후 테스트
5. **통합 테스트** — `pytest tests/ -v -k tutor`로 튜터 관련 테스트 실행
