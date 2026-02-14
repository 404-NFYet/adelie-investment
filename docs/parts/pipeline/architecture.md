# Data Pipeline 아키텍처

> datapipeline/ 디렉토리의 전체 구조, 18노드 LangGraph, 데이터 수집, LLM 클라이언트, 프롬프트, DB 저장을 다룬다.

---

## 디렉토리 구조

```
datapipeline/
├── graph.py            # LangGraph StateGraph 정의 (18노드 + 3 병렬 wrapper)
├── run.py              # 파이프라인 실행 진입점 (CLI)
├── config.py           # 환경변수 기반 설정 + KST 타임존
├── schemas.py          # Pydantic v2 스키마 (3개 인터페이스 계약)
├── __main__.py         # python -m datapipeline 진입점
├── nodes/              # LangGraph 노드 구현
│   ├── crawlers.py     # crawl_news_node, crawl_research_node
│   ├── screening.py    # screen_stocks_node
│   ├── curation.py     # summarize_news/research, curate_topics, build_curated_context
│   ├── interface1.py   # load_curated_context_node (파일 모드)
│   ├── interface2.py   # page_purpose, historical_case, narrative_body, validate
│   ├── interface3.py   # theme, pages, merge, glossary, hallcheck, tone, sources, assemble
│   ├── chart_agent.py  # run_chart_agent_node (6섹션 asyncio.gather)
│   └── db_save.py      # save_to_db_node (asyncpg)
├── data_collection/    # 데이터 수집 모듈
│   ├── news_crawler.py       # 뉴스 크롤링 (Google News 등)
│   ├── research_crawler.py   # 증권사 리서치 PDF 크롤링
│   ├── screener.py           # 가격 변동 스크리닝 (pykrx)
│   ├── news_summarizer.py    # 뉴스 요약
│   ├── openai_curator.py     # GPT-5.2 Web Search 큐레이션
│   ├── intersection.py       # 교차 검증
│   └── attention/            # Attention Scoring v3
│       ├── universe.py       # 유니버스 구성
│       ├── scoring.py        # 주목도 점수
│       └── media.py          # 미디어 노출 분석
├── ai/                 # LLM 클라이언트
│   ├── multi_provider_client.py  # OpenAI, Anthropic, Perplexity 통합
│   ├── llm_utils.py              # 유틸리티 (JSON 파싱, 재시도 등)
│   └── tools.py                  # LangChain tool 래퍼
├── db/                 # DB 저장
│   └── writer.py       # asyncpg 직접 저장 (5개 테이블)
├── collectors/         # 레거시 pykrx 수집기 (FastAPI sys.path 호환)
│   ├── stock_collector.py
│   └── financial_collector.py
├── scripts/            # 레거시 파이프라인 스크립트
│   ├── seed_fresh_data_integrated.py
│   └── generate_cases.py
├── prompts/            # 프롬프트 템플릿
│   ├── prompt_loader.py          # 프롬프트 로더 (frontmatter 파싱)
│   └── templates/                # .md 파일들
└── tests/              # 파이프라인 테스트
    ├── test_nodes.py
    ├── test_schemas.py
    ├── test_data_collection.py
    └── test_data_collection_utils.py
```

---

## 18노드 LangGraph 파이프라인

`datapipeline/graph.py`에 정의된 `StateGraph` 기반 통합 파이프라인이다.

### 노드 흐름

```
START
  ↓ route_data_source (input_path 유무 분기)
  ├── [파일 모드] load_curated_context ─────────────────────────────┐
  └── [수집 모드] collect_data_parallel ──┐                         │
                                          ↓                         │
                                   screen_stocks                    │
                                          ↓                         │
                                   summarize_parallel               │
                                          ↓                         │
                                   curate_topics                    │
                                          ↓                         │
                                   build_curated_context            │
                                          ↓                         │
                              ┌───────────┘ ←───────────────────────┘
                              ↓
                      run_page_purpose          (Interface 2)
                              ↓
                      run_historical_case
                              ↓
                      run_narrative_body
                              ↓
                      validate_interface2
                              ↓
                      run_theme                 (Interface 3)
                              ↓
                      run_pages
                              ↓
                      merge_theme_pages
                              ↓
                      glossary_and_chart_parallel
                        ├── glossary → hallcheck_glossary
                        └── chart_agent (6섹션 asyncio.gather)
                              ↓
                      run_tone_final
                              ↓
                      collect_sources
                              ↓
                      assemble_output
                              ↓
                      save_to_db
                              ↓
                             END
```

### 병렬 분기 (asyncio.gather wrapper)

| Wrapper 노드 | 내부 병렬 실행 |
|---------------|---------------|
| `collect_data_parallel` | `crawl_news` + `crawl_research` |
| `summarize_parallel` | `summarize_news` + `summarize_research` |
| `glossary_and_chart_parallel` | `glossary→hallcheck_glossary` + `chart_agent` |

### 에러 처리

각 노드 사이에 `check_error` 조건부 엣지가 있어 `state["error"]`가 설정되면 즉시 `END`로 라우팅된다.

### State 타입

`BriefingPipelineState(TypedDict)`로 정의되며, 주요 필드:

| 카테고리 | 필드 |
|---------|------|
| 입력 | `input_path`, `topic_index`, `backend`, `market` |
| 수집 결과 | `raw_news`, `raw_reports`, `screened_stocks`, `curated_topics` |
| Interface 1 | `curated_context` |
| Interface 2 | `page_purpose`, `historical_case`, `narrative`, `raw_narrative` |
| Interface 3 | `i3_theme`, `i3_pages`, `charts`, `pages`, `sources` |
| 출력 | `full_output`, `output_path`, `db_result` |
| 메타 | `error`, `metrics` |

---

## 3개 인터페이스 계약 (schemas.py)

`datapipeline/schemas.py`에 Pydantic v2로 정의된 인터페이스 계약이다.

### Interface 1: CuratedContext

데이터 수집 + 큐레이션 결과. 날짜/테마/선정 종목/뉴스/리서치/금융 개념을 포함한다.

```python
class CuratedContext(BaseModel):
    date: str
    theme: str
    one_liner: str
    selected_stocks: list[StockItem]
    verified_news: list[NewsItem]
    reports: list[ReportItem]
    concept: Concept
    source_ids: list[str]
```

### Interface 2: RawNarrative

LLM이 생성한 원시 내러티브. 역사적 사례 + 6섹션 본문.

```python
class RawNarrative(BaseModel):
    theme: str
    one_liner: str
    concept: Concept
    historical_case: HistoricalCase  # period, title, summary, outcome, lesson
    narrative: NarrativeBody         # 6섹션: background~summary
```

### Interface 3: FinalBriefing

최종 조립 결과. 6페이지 브리핑 + 차트 + 용어 + 출처 + 환각 체크.

```python
class FinalBriefing(BaseModel):
    theme: str
    one_liner: str
    generated_at: str
    pages: list[Page]                      # 6페이지, 각 Page에 chart/glossary 포함
    sources: list[SourceItem]
    hallucination_checklist: list[HallucinationItem]
```

---

## 데이터 수집 모듈 (data_collection/)

### 주요 모듈

| 모듈 | 역할 |
|------|------|
| `news_crawler.py` | Google News RSS 기반 뉴스 크롤링 |
| `research_crawler.py` | 증권사 리서치 PDF 크롤링 (네이버 증권) |
| `screener.py` | pykrx 기반 가격 변동 스크리닝 (단기 급등/급락, 중기 모멘텀, 거래량 급증) |
| `openai_curator.py` | GPT-5.2 Web Search로 종목-뉴스 교차 검증 + 토픽 큐레이션 |
| `news_summarizer.py` | Map/Reduce 뉴스 요약 |
| `intersection.py` | 스크리닝 결과와 뉴스의 교차점 분석 |

### Attention Scoring v3 (data_collection/attention/)

종목 주목도 점수 산출 모듈:
- `universe.py` — 유니버스 (KOSPI/KOSDAQ 상위 종목) 구성
- `scoring.py` — 가격/거래량/미디어 노출 복합 점수
- `media.py` — 미디어 노출 빈도 분석

### 스크리닝 설정 (config.py)

```python
SHORT_TERM_DAYS = 5          # 단기 관찰 기간
SHORT_TERM_RETURN_MIN = 5    # 단기 최소 등락률(%)
VOLUME_RATIO_MIN = 1.5       # 최소 거래량 배율
TOP_N = 20                   # 상위 종목 수
SCAN_LIMIT = 500             # 스캔 대상 종목 수
```

---

## LLM 클라이언트 (ai/)

### MultiProviderClient (multi_provider_client.py)

OpenAI, Perplexity, Anthropic을 통합 관리하는 싱글톤 클라이언트이다.

```python
client = get_multi_provider_client()
result = client.chat_completion(
    provider="openai",       # "openai" | "perplexity" | "anthropic"
    model="gpt-5-mini",
    messages=[...],
    thinking=True,           # GPT-5 계열 reasoning_effort
    temperature=0.7,
    max_tokens=4096,
)
```

### 프로바이더별 특성

| Provider | 초기화 | 호출 방식 |
|----------|--------|----------|
| OpenAI | `OpenAI(api_key=...)` | `chat.completions.create()` — GPT-5 계열은 `max_completion_tokens` 사용 |
| Perplexity | `OpenAI(base_url="https://api.perplexity.ai")` | OpenAI 호환 API |
| Anthropic | `Anthropic(api_key=...)` | `messages.create()` — system 메시지 분리 처리 |

### 모델 매핑 (config.py 기준)

| 단계 | Provider | 모델 | 용도 |
|------|----------|------|------|
| Phase 1 요약 | OpenAI | gpt-5-mini | 뉴스/리서치 Map/Reduce 요약 |
| Phase 2 큐레이션 | OpenAI | gpt-5.2 | Web Search 기반 토픽 큐레이션 |
| 내러티브 생성 (기본) | Anthropic | claude-sonnet-4 | Interface 2/3 본문 생성 |
| 차트 데이터 | OpenAI | gpt-5-mini | 차트 JSON 생성 |
| 리서치 PDF 요약 | OpenAI | gpt-5-mini | 증권사 리포트 요약 |

---

## 프롬프트 관리 (prompts/)

### 프롬프트 파일 형식

```markdown
---
provider: openai
model: gpt-5-mini
temperature: 0.7
thinking: true
---
{{include:_tone_guide}}
여기서부터 프롬프트 본문. {{variable}} 플레이스홀더 사용.
```

### 프롬프트 로더

```python
from datapipeline.prompts.prompt_loader import load_prompt

spec = load_prompt("page_purpose", topic="...", context="...")
# spec.provider, spec.model, spec.temperature, spec.messages
```

### 템플릿 목록

| 파일 | 인터페이스 | 역할 |
|------|-----------|------|
| `_tone_guide.md` | 공용 | 톤 가이드 (include용, frontmatter 없음) |
| `_chart_skeletons.md` | 공용 | 차트 스켈레톤 (include용) |
| `page_purpose.md` | Interface 2 | 6페이지 목적/구성 설계 |
| `historical_case.md` | Interface 2 | 역사적 사례 매칭 |
| `narrative_body.md` | Interface 2 | 본문 내러티브 생성 |
| `hallucination_check.md` | Interface 2 | 중간 환각 검증 |
| `final_hallucination.md` | Interface 3 | 최종 환각 검증 |
| `chart_generation.md` | Interface 3 | 차트 데이터 생성 |
| `glossary_generation.md` | Interface 3 | 용어 사전 생성 |
| `3_theme.md` | Interface 3 | 테마 생성 |
| `3_pages.md` | Interface 3 | 6페이지 분리 |
| `3_glossary.md` | Interface 3 | 용어 추출/생성 |
| `3_hallcheck_glossary.md` | Interface 3 | 용어 환각 검증 |
| `3_hallcheck_pages.md` | Interface 3 | 페이지 환각 검증 |
| `3_hallcheck_chart.md` | Interface 3 | 차트 환각 검증 |
| `3_tone_final.md` | Interface 3 | 최종 톤 조정 |
| `3_chart_generation.md` | Interface 3 | 차트 생성 (v2) |
| `3_chart_reasoning.md` | Interface 3 | 차트 추론 |

---

## DB 저장 (db/writer.py)

### 저장 테이블 매핑

`save_briefing_to_db(full_output)` 함수가 asyncpg로 직접 저장한다.

| 순서 | 테이블 | 설명 |
|------|--------|------|
| 1 | `daily_briefings` | 날짜별 브리핑 메타 (UPSERT — 동일 날짜 키워드 누적) |
| 2 | `briefing_stocks` | 선정 종목 (ON CONFLICT DO NOTHING) |
| 3 | `historical_cases` | 역사적 사례 (title, full_content, keywords JSONB) |
| 4 | `case_matches` | 키워드-사례 매칭 (theme + stock_code → case_id) |
| 5 | `case_stock_relations` | 사례-종목 관계 (main_subject / related) |

### 동시 쓰기 방지

동일 날짜 브리핑에 대한 race condition 방지를 위해 `pg_advisory_xact_lock`을 사용한다.

### JSONB 구조

- `daily_briefings.top_keywords` — `{"keywords": [{title, description, category, sector, stocks, ...}]}`
- `historical_cases.keywords` — `{theme, one_liner, concept, historical_case, comparison, narrative, sources, ...}`

---

## 실행 모드

### CLI 옵션

```bash
python -m datapipeline.run [OPTIONS]
```

| 옵션 | 값 | 기본값 | 설명 |
|------|-----|--------|------|
| `--backend` | `live` / `mock` / `auto` | `auto` | LLM 호출 방식 |
| `--market` | `KR` / `US` / `ALL` | `KR` | 대상 시장 |
| `--input` | 파일 경로 | - | curated context JSON (파일 모드) |
| `--topic-index` | 정수 | `0` | topics[] 배열 내 처리 인덱스 |
| `--topic-count` | 정수 | `3` | 생성할 카드(토픽) 수 |

### 실행 흐름 (데이터 수집 모드)

1. Topic 1: 전체 파이프라인 (데이터 수집 → Interface 2/3 → DB 저장)
2. `curated_topics`를 `output/curated_ALL_{date}.json`으로 저장
3. Topic 2~N: 저장된 curated_ALL 파일 로드 → Interface 2/3만 실행 (수집 생략)

### 실행 흐름 (파일 모드)

1. `--input path/to/curated.json` 지정
2. `load_curated_context` 노드에서 파일 로드
3. Interface 2/3 → DB 저장

### auto 모드

`OPENAI_API_KEY` 또는 `CLAUDE_API_KEY` 환경변수가 있으면 `live`, 없으면 `mock`으로 결정.

---

## KST 날짜 처리

서버가 UTC여도 KST 기준 날짜를 사용한다.

```python
from datapipeline.config import KST, kst_today

today = kst_today()  # KST 기준 오늘 날짜 (date 객체)
```

**주의**: `date.today()`, `datetime.now().date()` 사용 금지. 반드시 `kst_today()` 또는 `datetime.now(KST).date()` 사용.

---

## 환경변수 (config.py)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OPENAI_API_KEY` | (필수) | OpenAI API 키 |
| `PERPLEXITY_API_KEY` | (필수) | Perplexity API 키 |
| `CLAUDE_API_KEY` | (선택) | Anthropic API 키 |
| `DEFAULT_MODEL` | `claude-sonnet-4-20250514` | 내러티브 생성 기본 모델 |
| `CHART_MODEL` | `gpt-5-mini` | 차트 데이터 생성 모델 |
| `DATABASE_URL` | - | asyncpg 호환 PostgreSQL URL |
| `MARKET` | `KR` | 기본 시장 |
| `SHORT_TERM_DAYS` | `5` | 단기 스크리닝 기간 |
| `TOP_N` | `20` | 상위 종목 수 |
| `CURATED_TOPICS_MAX` | `5` | 큐레이션 최대 토픽 수 |
