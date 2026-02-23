# LangGraph 사용 현황

> 최종 업데이트: 2026-02-23

프로젝트 내 LangGraph가 사용되는 모듈은 두 곳이다.
튜터 챗봇 쪽에는 실험 코드(`tutor_agent.py`)와 프로덕션 코드(`tutor_engine.py`)가 분리되어 있다.

```
adelie-investment/
├── datapipeline/graph.py                    ← [프로덕션] 브리핑 생성 파이프라인 (LangGraph)
├── chatbot/agent/tutor_agent.py             ← [EXPERIMENTAL] LangGraph 튜터 (미사용)
└── fastapi/app/services/tutor_engine.py     ← [프로덕션] 튜터 엔진 (LangGraph 없음)
```

---

## 1. 데이터 파이프라인 (`datapipeline/graph.py`)

> 프로덕션에서 실제로 사용하는 LangGraph 그래프.
> 뉴스/리서치 수집 → 종목 스크리닝 → LLM 큐레이션 → 내러티브 생성 → DB 저장.

### State: `BriefingPipelineState`

| 그룹 | 주요 필드 |
|------|----------|
| 입력 | `input_path`, `topic_index`, `backend`, `market` |
| 데이터 수집 | `raw_news`, `raw_reports`, `screened_stocks`, `curated_topics`, `news_summary`, `research_summary` |
| Interface 2 | `page_purpose`, `historical_case`, `narrative`, `raw_narrative` |
| Interface 3 | `i3_theme`, `i3_pages`, `charts`, `pages`, `sources`, `hallucination_checklist` |
| 최종 출력 | `full_output`, `output_path`, `db_result` |
| 메타 | `error`, `metrics` (Annotated 병합 리듀서) |

### 그래프 흐름

```
START
  │
  ▼ route_data_source() [조건 라우터]
  ├─ input_path 있음 → load_curated_context ──────────────────┐
  └─ input_path 없음 → collect_data_parallel                  │
                           │ (crawl_news ‖ crawl_research)     │
                           ▼                                    │
                       screen_stocks                           │
                           │                                    │
                           ▼                                    │
                       summarize_parallel                      │
                           │ (summarize_news ‖ summarize_research)
                           ▼                                    │
                       curate_topics                           │
                           ▼                                    │
                       build_curated_context                   │
                           │                                    │
                           └──────────────────────────────────►│
                                                                │
                                                                ▼
                                                        run_page_purpose
                                                                ▼
                                                        run_historical_case
                                                                ▼
                                                        run_narrative_body
                                                                ▼
                                                        validate_interface2
                                                                ▼
                                                           run_theme
                                                                ▼
                                                           run_pages
                                                                ▼
                                                       merge_theme_pages
                                                                ▼
                                               glossary_and_chart_parallel
                                                 ├── glossary → hallcheck_glossary
                                                 └── chart_agent → hallcheck_chart
                                                                ▼
                                                         run_tone_final
                                                                ▼
                                                        run_home_icon_map
                                                                ▼
                                                        collect_sources
                                                                ▼
                                                        assemble_output
                                                                ▼
                                                          save_to_db
                                                                ▼
                                                              END
```

### 병렬 분기 (asyncio.gather wrapper)

| 병렬 노드 | 병렬 실행 대상 | 방식 |
|-----------|---------------|------|
| `collect_data_parallel` | crawl_news + crawl_research | `asyncio.to_thread` |
| `summarize_parallel` | summarize_news + summarize_research | `asyncio.to_thread` |
| `glossary_and_chart_parallel` | glossary→hallcheck + chart_agent→hallcheck | `asyncio.gather` |

### 에러 전파

모든 주요 노드 뒤에 `check_error()` 조건 라우터가 붙어 있다.
`state["error"]` 가 존재하면 다음 노드로 진행하지 않고 즉시 `END`로 단락된다.

차트 hallcheck 실패 시: 차트를 `None`으로 처리하고 파이프라인은 계속 진행 (엄격 게이트).

### Checkpointer

- Redis `AsyncRedisSaver` 사용 (`REDIS_URL` 환경변수)
- Redis 미연결 시 `None` 반환 → checkpointing 비활성화 (graceful fallback)

---

## 2. 튜터 에이전트 (`chatbot/agent/tutor_agent.py`)

> **[EXPERIMENTAL]** — 프로덕션 미사용.
> 향후 LangGraph 기반 튜터로 마이그레이션하기 위한 실험 코드.

### State: `AgentState`

| 필드 | 타입 | 설명 |
|------|------|------|
| `messages` | `Sequence` | `add_messages` 리듀서 (누적 append) |
| `difficulty` | `str` | `"beginner"` \| `"elementary"` \| `"intermediate"` |
| `context_type` | `Optional[str]` | `"briefing"` \| `"case"` \| `"comparison"` \| `"glossary"` |
| `context_id` | `Optional[int]` | 컨텍스트 레코드 ID |

### 그래프 흐름 (ReAct 패턴)

```
START
  │
  ▼
agent  ────── tool_calls 있음? ──► tools
  ▲                                   │
  └───────────────────────────────────┘  (루프)
  │
  └── tool_calls 없음 ──────────────► END
```

조건 라우터 `_should_continue()`:
- `last_message.tool_calls` 존재 → `"continue"` → tools 노드
- 없음 → `"end"` → END

### 도구 5개

| 도구 | 파일 | 역할 |
|------|------|------|
| `get_glossary` | `tools/glossary_tool.py` | 금융 용어 목록 조회 |
| `lookup_term` | `tools/glossary_tool.py` | 특정 용어 상세 조회 |
| `search_historical_cases` | `tools/search_tool.py` | 과거 사례 검색 |
| `get_today_briefing` | `tools/briefing_tool.py` | 오늘 브리핑 조회 |
| `compare_past_present` | `tools/comparison_tool.py` | 과거↔현재 비교 |

### 시스템 프롬프트 로드 순서

```
1순위: chatbot/prompts/templates/tutor_system.md
       + tutor_{difficulty}.md (beginner / elementary / intermediate)
2순위: 내장 폴백 문자열 (ImportError / FileNotFoundError 시)
```

### 실행 모드

| 메서드 | 방식 | 반환 |
|--------|------|------|
| `invoke()` | 동기 | 최종 `AIMessage.content` 문자열 |
| `astream()` | 비동기 | SSE 이벤트 dict yield |

`astream` 이벤트 타입:

| 타입 | 발생 시점 |
|------|----------|
| `thinking` | 스트리밍 시작 시 |
| `tool_call` | LLM이 도구 호출 결정 |
| `tool_result` | 도구 실행 완료 (100자 preview) |
| `text_delta` | 최종 텍스트 응답 |
| `done` | 그래프 종료 |

### Checkpointer

생성자 인자로 주입하는 방식:
- 없으면 → 매 호출마다 새 세션 (무상태)
- 있으면 → `astream` 호출 시 `thread_id`로 세션별 메시지 히스토리 유지

---

## 3. 프로덕션 튜터 (`fastapi/app/services/tutor_engine.py`)

> LangGraph를 사용하지 않음.
> `chatbot/` 모듈에서 `visualization_tool.py`만 import해서 차트 생성에 활용.

### 처리 흐름 (순차 함수)

```
generate_tutor_response(request, db)
  │
  ├─ 1. 용어 감지 → Glossary DB 조회
  │      (PER, PBR, EPS, ROE, ROA, ETF, 배당, 시가총액)
  │
  ├─ 2. 사례(HistoricalCase) + 리포트(BrokerReport) DB 검색
  │
  ├─ 3. 종목 코드 감지 → pykrx 주가 조회 + 재무지표 수집
  │
  ├─ 4. 시스템 프롬프트 조립
  │      = 난이도 프롬프트 + 보안 지침 + 용어 컨텍스트 + DB 컨텍스트
  │
  ├─ 5. 이전 대화 DB 로드 (최근 20개 메시지)
  │
  ├─ 6. OpenAI gpt-4o-mini 스트리밍
  │      → SSE: text_delta 청크 yield
  │
  ├─ 7. 세션/메시지 DB 저장 + Redis 캐시 무효화
  │
  ├─ 8. 출처 목록 SSE 전송 (glossary / case / report / stock_price / financial)
  │
  └─ 9. 자동 시각화 (종목 감지 + 주가 데이터 있을 때)
         └─ _generate_with_claude() → fallback: _generate_with_openai()
            → code_executor 실행 → MinIO 저장
            → SSE: visualization (html) yield
```

---

## 비교 요약

| 항목 | 데이터 파이프라인 | 튜터 에이전트 | 프로덕션 튜터 |
|------|:---------------:|:-----------:|:-----------:|
| **LangGraph** | ✅ | ✅ | ❌ |
| **프로덕션 사용** | ✅ | ❌ | ✅ |
| **그래프 패턴** | 선형 DAG + 병렬 분기 | ReAct (agent↔tools 루프) | 순차 함수 |
| **노드 수** | 18개 | 2개 | — |
| **Checkpointer** | Redis (선택) | 주입 방식 (선택) | DB 직접 저장 |
| **스트리밍** | 없음 (배치 실행) | `astream` SSE | OpenAI SSE |
| **메모리 관리** | — | 윈도우 40개 (20턴) | DB 최근 20개 |
