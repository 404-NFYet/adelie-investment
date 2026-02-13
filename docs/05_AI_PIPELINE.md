# AI 파이프라인 가이드

## 아키텍처 개요

### 18노드 LangGraph 파이프라인

`datapipeline/graph.py`에 정의된 StateGraph 기반 통합 파이프라인입니다.
뉴스/리서치 크롤링 → 종목 스크리닝 → LLM 큐레이션 → 내러티브 생성 → DB 저장까지 단일 그래프로 실행됩니다.

```
START
  ↓ (route_data_source: 파일 입력 시 load_curated_context, 아니면 데이터 수집)
  ├── Data Collection (7노드)
  │   crawl_news → crawl_research → screen_stocks → summarize_news
  │   → summarize_research → curate_topics → build_curated_context
  │
  ├── Interface 1 (1노드, 파일 입력 모드)
  │   load_curated_context
  │
  ├── Interface 2 (4노드)
  │   run_page_purpose → run_historical_case → run_narrative_body → validate_interface2
  │
  ├── Interface 3 (6노드)
  │   build_charts → build_glossary → assemble_pages → collect_sources
  │   → run_final_check → assemble_output
  │
  └── DB Save (1노드)
      save_to_db → END
```

각 단계 사이에 에러 체크 분기가 있어, 실패 시 조기 종료합니다.

## 실행 방법

### 새 LangGraph 파이프라인

```bash
# 실서비스 (API 키 필요)
python -m datapipeline.run --backend live --market KR

# 테스트 (LLM 미호출, mock 데이터 사용)
python -m datapipeline.run --backend mock

# 파일 입력 모드 (curated context JSON 직접 지정)
python -m datapipeline.run --input path/to/curated.json --backend live

# 자동 모드 (API 키 존재 시 live, 없으면 mock)
python -m datapipeline.run --backend auto --market KR
```

**CLI 옵션:**

| 옵션 | 값 | 설명 |
|------|-----|------|
| `--backend` | `live` / `mock` / `auto` | LLM 호출 방식 (기본: auto) |
| `--market` | `KR` / `US` / `ALL` | 대상 시장 (기본: KR) |
| `--input` | 파일 경로 | curated context JSON (파일 모드) |
| `--topic-index` | 정수 | topics[] 배열 내 처리 대상 인덱스 (기본: 0) |

### 레거시 스크립트 (deploy-test 수동 실행용)

```bash
# Step 1: 시장 데이터 수집
docker exec adelie-backend-api python /app/scripts/seed_fresh_data_integrated.py

# Step 2: 역사적 사례 생성 (OPENAI_API_KEY 필요)
docker exec adelie-backend-api python /app/scripts/generate_cases.py
```

## 용어 생성 방식: 동적 LLM

정적 DB 용어사전 대신 LLM이 동적으로 용어를 설명합니다.

**용어 마킹 형식**: `<mark class='term'>용어</mark>`

**파이프라인 흐름**:
1. Writer가 `<mark class='term'>용어</mark>` 포함하여 내러티브 생성
2. `extract_terms()` — 생성된 내러티브에서 용어 추출
3. `generate_glossary()` — 추출된 용어들의 정의를 LLM으로 일괄 생성
4. `sanitize_marks()` — 사전에 없는 용어의 마크 태그 제거
5. 최종 데이터에 용어 + 정의를 함께 저장

**챗봇 용어 설명**: 사용자가 질문하면 LLM이 응답 내에서 자연스럽게 괄호 설명 추가.
DB에서 검색 실패 시 LLM이 동적으로 생성하고 Redis에 24시간 캐싱.

## 프롬프트 관리

### 구조

```
datapipeline/prompts/
  prompt_loader.py          # 파이프라인 프롬프트 로더
  templates/
    _tone_guide.md          # 공용 톤 가이드
    _chart_skeletons.md     # 차트 스켈레톤 (include용)
    page_purpose.md         # 페이지 목적/구성 설계
    historical_case.md      # 역사적 사례 매칭
    narrative_body.md       # 본문 내러티브 생성
    hallucination_check.md  # 환각 검증 (중간)
    final_hallucination.md  # 최종 환각 검증
    chart_generation.md     # 차트 데이터 생성
    glossary_generation.md  # 용어 사전 생성

chatbot/prompts/
  prompt_loader.py          # 튜터 프롬프트 로더
  templates/
    _tone_guide.md          # 공용 톤 가이드
    tutor_system.md         # 튜터 시스템 프롬프트
    tutor_beginner.md
    tutor_intermediate.md
    tutor_elementary.md
    search_historical.md
    term_explanation.md
```

### 프롬프트 파일 형식

```markdown
---
provider: openai
model: gpt-5-mini
temperature: 0.7
thinking: true
---
{{include:_tone_guide}}
{{variable}} 플레이스홀더
```

### 사용법

```python
from datapipeline.prompts import load_prompt  # 파이프라인용
from chatbot.prompts import load_prompt       # 튜터용
spec = load_prompt("page_purpose", topic="...", context="...")
```

## 모델 매핑

`datapipeline/config.py` 기준:

| 단계 | Provider | 모델 | 용도 |
|------|----------|------|------|
| Phase 1 요약 | OpenAI | gpt-5-mini | 뉴스/리서치 요약 |
| Phase 2 큐레이션 | OpenAI | gpt-5.2 | 웹 검색 큐레이션 |
| 내러티브 | Anthropic | claude-sonnet-4 | 본문 생성 (기본 모델) |
| 차트 | OpenAI | gpt-4o-mini | 차트 데이터 생성 |
| 튜터 | OpenAI | gpt-4o-mini | 질문 응답 |

## 파일 구조

```
datapipeline/
├── graph.py            # LangGraph StateGraph 정의 (18노드)
├── run.py              # 파이프라인 실행 진입점 (CLI)
├── config.py           # 환경변수 기반 설정 + 모델 매핑
├── schemas.py          # Pydantic 스키마 (PipelineState 등)
├── __main__.py         # python -m datapipeline 진입점
├── nodes/              # LangGraph 노드 구현
│   ├── crawlers.py     # crawl_news, crawl_research
│   ├── screening.py    # screen_stocks
│   ├── curation.py     # summarize_*, curate_topics, build_curated_context
│   ├── interface1.py   # load_curated_context (파일 모드)
│   ├── interface2.py   # page_purpose, historical_case, narrative_body, validate
│   ├── interface3.py   # charts, glossary, assemble, sources, final_check, output
│   └── db_save.py      # save_to_db (asyncpg)
├── data_collection/    # 데이터 수집 모듈
│   ├── news_crawler.py
│   ├── research_crawler.py
│   ├── screener.py
│   └── openai_curator.py
├── ai/                 # LLM 클라이언트
│   ├── multi_provider_client.py  # OpenAI, Anthropic, Perplexity
│   └── llm_utils.py              # 유틸리티
├── db/                 # DB 저장
│   └── writer.py       # asyncpg 직접 저장
├── collectors/         # 레거시 pykrx 수집기 (FastAPI sys.path 호환)
├── scripts/            # 레거시 파이프라인 스크립트
│   ├── seed_fresh_data_integrated.py
│   └── generate_cases.py
├── prompts/            # 프롬프트 템플릿
│   ├── prompt_loader.py
│   └── templates/      # 9개 .md 파일
└── tests/              # 파이프라인 테스트
    ├── test_nodes.py
    ├── test_schemas.py
    ├── test_data_collection.py
    └── test_data_collection_utils.py
```
