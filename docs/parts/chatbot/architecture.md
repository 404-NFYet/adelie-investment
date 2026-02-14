# Chatbot 아키텍처

## 개요

AI 튜터 챗봇은 두 가지 구현이 공존한다.

| 구현 | 경로 | 상태 | 설명 |
|------|------|------|------|
| 프로덕션 엔진 | `fastapi/app/services/tutor_engine.py` | **현재 사용 중** | OpenAI 직접 호출 + SSE 스트리밍 |
| LangGraph 에이전트 | `chatbot/agent/tutor_agent.py` | 실험 단계 | LangGraph StateGraph 기반, 향후 마이그레이션 대상 |

두 구현 모두 `chatbot/tools/`의 도구와 `chatbot/prompts/templates/`의 프롬프트를 공유한다.

## 디렉토리 구조

```
chatbot/
├── agent/
│   ├── tutor_agent.py      # LangGraph StateGraph (실험)
│   ├── prompts.py           # 시스템 프롬프트 생성 함수
│   └── checkpointer.py     # AsyncPostgresSaver 체크포인터
├── tools/
│   ├── briefing_tool.py     # 브리핑 조회 도구
│   ├── comparison_tool.py   # 과거-현재 비교 도구
│   ├── glossary_tool.py     # 용어 사전 도구
│   ├── search_tool.py       # 히스토리컬 케이스 검색 도구
│   └── visualization_tool.py # 차트 생성 도구 (Claude/OpenAI)
├── services/
│   └── term_highlighter.py  # 응답 텍스트 내 용어 감지 + 하이라이트
├── prompts/
│   ├── prompt_loader.py     # 마크다운 템플릿 로더
│   └── templates/
│       ├── tutor_system.md      # 시스템 프롬프트 (공통)
│       ├── tutor_beginner.md    # 초급자 난이도
│       ├── tutor_elementary.md  # 초중급 난이도
│       ├── tutor_intermediate.md # 중급 난이도
│       ├── search_historical.md  # 검색 도구 프롬프트
│       ├── term_explanation.md   # 용어 설명 프롬프트
│       └── _tone_guide.md       # 톤 가이드 (공통 참조)
├── core/
│   ├── config.py            # 환경 설정
│   └── langsmith_config.py  # LangSmith 추적 설정
└── pyproject.toml
```

## LangGraph 에이전트 구조 (실험)

### State
```python
class AgentState(TypedDict):
    messages: Annotated[Sequence, add_messages]  # 대화 이력
    difficulty: str           # 난이도 (beginner/elementary/intermediate)
    context_type: Optional[str]   # 컨텍스트 종류 (keyword/case/narrative)
    context_id: Optional[int]     # 컨텍스트 ID
```

### 그래프 흐름
```
START → agent_node → should_continue?
                         ├─ (도구 호출 필요) → tool_node → agent_node
                         └─ (응답 완료) → END
```

- `agent_node`: LLM에 메시지 전달, 도구 호출 여부 판단
- `tool_node`: LangChain `ToolNode`로 도구 실행
- `should_continue`: `AIMessage.tool_calls` 유무로 분기

## 도구 (Tools) 목록

| 도구 | 파일 | 기능 |
|------|------|------|
| `get_glossary` | `glossary_tool.py` | DB에서 용어 정의 조회 |
| `lookup_term` | `glossary_tool.py` | 단일 용어 상세 설명 |
| `search_historical_cases` | `search_tool.py` | 과거 유사 사례 검색 |
| `get_briefing` | `briefing_tool.py` | 오늘의 브리핑/키워드 조회 |
| `compare_cases` | `comparison_tool.py` | 과거-현재 케이스 비교 |
| `generate_visualization` | `visualization_tool.py` | 주가/지표 차트 생성 (Claude/OpenAI) |

## SSE 스트리밍 흐름 (프로덕션)

```
[Frontend]                     [Nginx]                    [FastAPI]              [OpenAI]
    │                             │                           │                      │
    ├─ POST /api/v1/tutor/chat ──►│                           │                      │
    │                             ├── proxy_pass ────────────►│                      │
    │                             │   (proxy_buffering off)   │                      │
    │                             │                           ├── stream request ───►│
    │                             │                           │                      │
    │  ◄── SSE: content ─────────┤◄── SSE: content ──────────┤◄── token chunk ──────┤
    │  ◄── SSE: content ─────────┤◄── SSE: content ──────────┤◄── token chunk ──────┤
    │  ◄── SSE: chart ───────────┤◄── SSE: chart ────────────┤  (auto-visualization)│
    │  ◄── SSE: done ────────────┤◄── SSE: done ─────────────┤◄── [DONE] ──────────┤
    │                             │                           │                      │
```

### SSE 이벤트 포맷
```
event: content
data: {"token": "안녕하세요"}

event: chart
data: {"chart_url": "/charts/abc123.html", "title": "삼성전자 주가 추이"}

event: done
data: {"session_id": "uuid", "message_id": "uuid"}

event: error
data: {"message": "에러 메시지"}
```

### 핵심 처리 흐름 (`tutor_engine.py`)
1. 요청 수신 → 세션 생성/조회 (DB)
2. 컨텍스트 수집 — 현재 페이지의 키워드/케이스/내러티브 데이터
3. 난이도별 시스템 프롬프트 구성
4. 자동 시각화 판단 — 종목 코드 감지 시 차트 자동 생성
5. OpenAI 스트리밍 호출 → SSE로 토큰 전달
6. 응답 완료 → DB에 메시지 저장

## 프롬프트 체계

### 템플릿 구조
프롬프트 템플릿은 `chatbot/prompts/templates/`에 마크다운 파일로 관리한다. frontmatter에 메타데이터를 포함할 수 있다.

### 난이도별 프롬프트
| 난이도 | 템플릿 | 특징 |
|--------|--------|------|
| beginner | `tutor_beginner.md` | 일상적 비유, 전문용어 최소화 |
| elementary | `tutor_elementary.md` | 기초 개념 포함, 쉬운 설명 |
| intermediate | `tutor_intermediate.md` | 전문 분석, 데이터 기반 설명 |

### 톤 가이드
`_tone_guide.md`에 공통 톤/스타일 가이드를 정의하고, 각 난이도 프롬프트에서 참조한다.

## 체크포인터 (세션 영속화)

- `checkpointer.py`에서 `AsyncPostgresSaver`를 사용하여 LangGraph 세션을 PostgreSQL에 저장
- 현재 실험 단계 — 프로덕션 엔진(`tutor_engine.py`)은 자체 `TutorSession`/`TutorMessage` 모델로 세션 관리
- DATABASE_URL에서 asyncpg 드라이버를 psycopg로 변환하여 사용

## FastAPI 인터페이스

챗봇은 독립 모듈이지만, FastAPI에서 다음과 같이 통합된다.

| FastAPI 경로 | 연결 |
|-------------|------|
| `app/services/tutor_engine.py` | 프로덕션 엔진 — OpenAI 직접 호출 |
| `app/api/routes/tutor.py` | `/api/v1/tutor/*` 라우트 정의 |
| `app/models/tutor.py` | TutorSession, TutorMessage 모델 |
| `app/schemas/tutor.py` | TutorChatRequest 등 Pydantic 스키마 |

`tutor_engine.py`는 `chatbot/tools/visualization_tool.py`를 `sys.path`로 임포트하여 차트 생성 기능을 사용한다.
