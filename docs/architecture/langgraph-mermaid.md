# 에이전트 & 챗봇 전체 흐름 (Mermaid)

> 최종 업데이트: 2026-02-23

---

## 1. Agent Canvas — 프론트엔드 진입 흐름

```mermaid
flowchart TD
    A([사용자]) --> B{진입 경로}
    B -->|홈 키워드 클릭| C[mode = home]
    B -->|종목 상세| D[mode = stock]
    B -->|교육 화면| E[mode = education]

    C --> F[sessionStorage\nadelivered_home_context 로드]
    D --> G[location.state.stockContext 로드]
    E --> H[sessionStorage\nadelied_education_context 로드]

    F & G & H --> I[buildAgentContextEnvelope\nui_snapshot + action_catalog\n+ interaction_state 조립]

    I --> J{initialPrompt\n있음?}
    J -->|있음| K[sendCanvasMessage 자동 실행]
    J -->|없음| L[사용자 직접 입력 대기]

    K & L --> M[useTutor.sendMessage\nsession_id, difficulty, chatOptions]
    M --> N[POST /api/v1/tutor/route\n라우터 판단]
    N --> O{decision}
    O -->|inline_reply| P[ChatFAB 인라인 텍스트]
    O -->|inline_action| Q[executeAction\nuseAgentControlOrchestrator]
    O -->|open_canvas| R[POST /api/v1/tutor/chat\nSSE 스트리밍]

    Q --> S[Tool 실행 결과 → sendCanvasMessage]
    S --> R

    R --> T[SSE 이벤트 수신]
    T --> U[AgentCanvasSections 렌더링]

    U --> V{turn 탐색}
    V -->|좌우 스와이프\n또는 버튼| W[activeTurnIndex ±1\nswipeToast 표시]
    W --> U

    U --> X[텍스트 선택\nSelectionAskChip]
    X --> Y[선택 텍스트 → sendCanvasMessage]
    Y --> R

    U --> Z[저장 버튼]
    Z --> ZA[POST /api/v1/tutor/sessions/:id/pin\n+ learningApi.upsertProgress\n+ localStorage 복습 메타 저장]
```

---

## 2. 프로덕션 튜터 응답 흐름 (`/api/v1/tutor/chat`)

```mermaid
flowchart TD
    START([POST /api/v1/tutor/chat]) --> A[generate_tutor_response]
    A --> B[SSE yield: thinking]

    B --> C[run_guardrail\nguardrail_policy: soft / strict]
    C --> D{hard_block?}
    D -->|Yes| E[SSE yield: block_message → done\n종료]
    D -->|No, soft_notice| F[SSE yield: guardrail_notice]
    D -->|SAFE| G

    F --> G[_collect_context]

    subgraph CTX [컨텍스트 수집]
        G --> G1[_collect_glossary_context\nPER·PBR·EPS 등 용어 DB]
        G --> G2[_collect_db_context\nHistoricalCase + BrokerReport]
        G --> G3[detect_stock_codes\npykrx 주가 + 재무지표]
        G --> G4[_collect_stock_lookup_context\nstock_listings 화이트리스트]
        G --> G5[collect_stock_intelligence\n투자 인텔 수집]
    end

    G1 & G2 & G3 & G4 & G5 --> H[_build_llm_messages]

    subgraph MSG [메시지 구성]
        H --> H1[get_difficulty_prompt\nbeginner / elementary / intermediate]
        H --> H2[page_context 주입\ncontext_text or DB fallback]
        H --> H3[출력 형식 규칙\nMarkdown · LaTeX · Table]
        H --> H4[canvas_markdown 모드 추가 규칙]
        H --> H5[guardrail soft 지침 추가]
        H --> H6[이전 대화 로드\nTutorMessage 최근 30개\n토큰 기반 윈도우 ~6000자]
    end

    H1 & H2 & H3 & H4 & H5 & H6 --> I{TUTOR_USE_RESPONSES_API?}

    I -->|Yes| J[client.responses.create\nstream=True\n선택: web_search_preview]
    I -->|No| K[client.chat.completions.create\nstream=True]

    J --> L{이벤트 타입}
    L -->|output_text.delta| M[SSE yield: text_delta]
    L -->|web_search 이벤트| N[SSE yield: tool_call 웹검색]
    N --> M
    L -->|response.completed| O[total_tokens 추출]
    L -->|Responses API 오류| K

    K --> P[chunk.delta.content]
    P --> M

    M --> Q[_save_tutor_session]

    subgraph SAVE [DB 저장]
        Q --> Q1[TutorSession upsert\n커버 메타 갱신]
        Q --> Q2[TutorMessage 2건 insert\nuser + assistant]
        Q --> Q3[Redis 캐시 무효화]
        Q --> Q4{10턴마다}
        Q4 -->|Yes| Q5[대화 요약 gpt-4o-mini\n+ 엔티티 추출]
    end

    Q1 & Q2 & Q3 --> R{should_auto_visualize\n+ chart_data?}

    R -->|Yes| S[시각화 자동 생성]

    subgraph VIZ [자동 시각화]
        S --> S1{CLAUDE_API_KEY?}
        S1 -->|Yes| S2[claude-3-5-haiku\nPlotly JSON 생성]
        S1 -->|No| S3[gpt-4o-mini\nPlotly JSON fallback]
        S2 & S3 --> S4[JSON 파싱]
        S4 --> S5[SSE yield: visualization\nformat: json + chartData]
    end

    R -->|No| T

    S5 --> T[structured_extract\n_extract_structured_from_markdown]
    T --> U[_recommend_actions\n매수·매도·포트폴리오·네비게이션 추천]
    U --> V[SSE yield: done\nsession_id · tokens · sources\n· structured · actions · model]
```

---

## 3. 라우터 판단 흐름 (`/api/v1/tutor/route`)

```mermaid
flowchart TD
    A([POST /api/v1/tutor/route]) --> B[_route_with_llm]
    B --> C[gpt-4o-mini\nJSON mode, temp=0.1]

    C --> D[_normalize_route_response]
    D --> E{confidence\n≥ threshold?}
    E -->|No| F[decision = inline_reply\n낮은 신뢰도 fallback]

    E -->|Yes| G{decision}
    G -->|inline_action| H{action_id가\naction_catalog에 있음?}
    H -->|No| F
    H -->|Yes| I[inline_action 반환]

    G -->|inline_reply| J[inline_text 반환]
    G -->|open_canvas| K[canvas_prompt 반환\n→ 캔버스 전환 트리거]

    F & I & J & K --> L([TutorRouteResponse])
```

---

## 4. 데이터 파이프라인 LangGraph (`datapipeline/graph.py`)

```mermaid
flowchart TD
    START([START]) --> ROUTE{route_data_source\ninput_path 유무}

    ROUTE -->|파일 로드| N01[load_curated_context\nInterface 1]
    ROUTE -->|데이터 수집| N02[collect_data_parallel]

    subgraph PAR1 [병렬 asyncio.gather]
        N02 --> P1[crawl_news_node]
        N02 --> P2[crawl_research_node]
    end
    P1 & P2 --> N03[screen_stocks]
    N03 -->|error?| ERR1([END])
    N03 --> N04[summarize_parallel]

    subgraph PAR2 [병렬 asyncio.gather]
        N04 --> P3[summarize_news_node]
        N04 --> P4[summarize_research_node]
    end
    P3 & P4 --> N05[curate_topics]
    N05 -->|error?| ERR2([END])
    N05 --> N06[build_curated_context]
    N06 -->|error?| ERR3([END])
    N06 --> N07

    N01 -->|error?| ERR4([END])
    N01 --> N07[run_page_purpose]

    N07 -->|error?| ERR5([END])
    N07 --> N08[run_historical_case]
    N08 -->|error?| ERR6([END])
    N08 --> N09[run_narrative_body]
    N09 -->|error?| ERR7([END])
    N09 --> N10[validate_interface2]
    N10 -->|error?| ERR8([END])

    N10 --> N11[run_theme]
    N11 --> N12[run_pages]
    N12 --> N13[merge_theme_pages]
    N13 --> N14[glossary_and_chart_parallel]

    subgraph PAR3 [병렬 asyncio.gather]
        N14 --> G1[run_glossary_node]
        G1 --> G2[run_hallcheck_glossary_node]
        N14 --> C1[run_chart_agent_node\n6섹션 병렬]
        C1 --> C2[run_hallcheck_chart_node]
        C2 -->|검증 실패| C3[charts = None\n엄격 게이트]
    end

    G2 & C2 & C3 --> N15[run_tone_final]
    N15 --> N16[run_home_icon_map]
    N16 --> N17[collect_sources]
    N17 --> N18[assemble_output]
    N18 --> N19[save_to_db]
    N19 --> END2([END])
```

---

## 5. 실험적 튜터 에이전트 LangGraph (`chatbot/agent/tutor_agent.py`)

> **[EXPERIMENTAL]** 프로덕션 미사용. ReAct 패턴 구현.

```mermaid
flowchart TD
    START([START]) --> AGENT

    subgraph AGENT_NODE [agent 노드]
        AGENT[agent] --> A1[메시지 윈도우\n최근 40개 유지]
        A1 --> A2[get_system_prompt\ndifficulty 기반]
        A2 --> A3[llm_with_tools.invoke\ngpt-4o-mini + tools 바인딩]
    end

    A3 --> COND{_should_continue\ntool_calls 있음?}
    COND -->|Yes: continue| TOOLS

    subgraph TOOL_NODE [tools 노드]
        TOOLS[ToolNode] --> T1[get_glossary]
        TOOLS --> T2[lookup_term]
        TOOLS --> T3[search_historical_cases]
        TOOLS --> T4[get_today_briefing]
        TOOLS --> T5[compare_past_present]
    end

    T1 & T2 & T3 & T4 & T5 --> AGENT

    COND -->|No: end| END_NODE([END])

    subgraph STREAM [astream 이벤트]
        AGENT -->|tool_calls 있음| EV1[yield: tool_call\ntool · args]
        TOOLS --> EV2[yield: tool_result\n100자 preview]
        A3 -->|최종 응답| EV3[yield: text_delta\ncontent]
        END_NODE --> EV4[yield: done]
    end
```

---

## 시스템 전체 연결 구조

```mermaid
flowchart LR
    USER([사용자]) <-->|모바일 UI\nmobile-first| FE

    subgraph FE [Frontend\nReact 19 + Vite]
        FE1[AgentCanvasPage]
        FE2[useTutor Context]
        FE3[AgentCanvasSections]
        FE1 --> FE2 --> FE3
    end

    FE <-->|SSE 스트리밍\nJSON 이벤트| BE

    subgraph BE [Backend\nFastAPI :8082]
        BE1[POST /tutor/route\n라우터 판단]
        BE2[POST /tutor/chat\nSSE 스트리밍]
        BE3[generate_tutor_response\n프로덕션 튜터 엔진]
        BE1 --> BE2 --> BE3
    end

    BE3 <--> LLM[OpenAI\ngpt-4o-mini\nResponses API]
    BE3 <--> VIZ[Anthropic Claude\nclaude-3-5-haiku\n시각화 생성]
    BE3 <--> DB[(PostgreSQL\nTutorSession\nTutorMessage\nGlossary\nHistoricalCase)]
    BE3 <--> CACHE[(Redis\n세션 캐시\n용어 캐시)]

    subgraph PIPE [Data Pipeline\n별도 프로세스]
        DP[datapipeline/run.py\nLangGraph 18노드]
        DP --> DB
    end

    subgraph EXP [EXPERIMENTAL]
        TA[chatbot/agent\ntutor_agent.py\nLangGraph ReAct]
    end

    PIPE -.->|브리핑 데이터 공급| DB
    BE3 -.->|visualization_tool만 import| EXP
```
