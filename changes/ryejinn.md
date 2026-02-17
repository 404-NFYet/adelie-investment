# 안례진 (ryejinn) — 프로젝트 변경이력

> 역할: 파이프라인 QA / AI 개발
> 기간: 2026-01-20 ~ 현재 (개발 진행 중)
> 기술 스택: LangGraph, OpenAI, Perplexity, Google Gemini, Claude, asyncpg, pytest, Playwright, LangSmith

---

## Phase 1: QA 기반 구축 — 테스트 인프라·요구사항·AI 도구 (02-03 ~ 02-07)

### Situation
프로젝트 초기에 AI 기반 금융 콘텐츠 생성 플랫폼이라는 특성상 LLM 출력의 품질 보증(환각 검증, 정확성 테스트)이 필수적이었으나, 테스트 인프라가 전무한 상태였다. PRD 수준의 요구사항 명세가 부족하여 팀 전체의 구현 방향 기준이 모호했고, LLM 에이전트의 동작을 추적할 관측 도구도 부재하였다. 데이터 수집 소스 역시 단일 경로에 의존하고 있어 다각화가 필요했다.

### Task
- PRD Phase 0~1 요구사항 상세화 및 기능 명세 작성
- AI 환각 검증 테스트 프레임워크 설계 및 구현
- API 통합 테스트, 헬스체크, 스모크 테스트, E2E 테스트 작성
- Perplexity 기반 투자 사례 수집기 개발
- LangSmith 트레이싱 설정 및 용어집/검색 도구 구현
- 시각화 모델 비교 테스트 작성
- 팀 운영 문서 및 테스트 가이드 작성

### Action
PRD Phase 0~1 요구사항을 상세화하여 MVP 핵심 기능(키워드 조회, 내러티브 열람, AI 튜터 대화)의 범위를 정의하고, Phase 1 확장 기능(포트폴리오, 리더보드, 학습 리포트)의 인수 조건을 명시하였다. 이를 통해 팀 전체가 구현 방향을 공유할 수 있는 기준 문서를 확립하였다.

AI 환각 검증 테스트 프레임워크를 설계하여, LLM이 생성하는 역사적 투자 사례의 날짜 유효성, 종목코드 실존 여부, 이벤트 팩트 체크를 자동화하는 테스트 케이스를 작성하였다. API 통합 테스트에서는 키워드, 케이스, 인증, 용어집 엔드포인트의 정상·에러 시나리오를 커버하였다. Playwright 기반 E2E 테스트에서는 랜딩 → 키워드 선택 → 내러티브 조회 → 튜터 질문의 전체 사용자 플로우를 480px 모바일 뷰포트에서 검증하였다. 헬스체크·스모크 테스트로 배포 후 검증 체계도 구축하였다. 시각화 모델 비교 테스트(353라인)에서는 GPT-4, Claude, Perplexity 모델의 차트 데이터 생성 품질을 생성 속도, 데이터 정확도, JSON 포맷 준수율 기준으로 비교 분석하였다.

Perplexity API 기반 투자 사례 수집기(+499라인)를 개발하여 웹 검색 기반의 사실적 데이터 확보 경로를 추가하였다. LangSmith 트레이싱을 설정하여 AI 에이전트의 의사결정 과정, 도구 호출 순서, 토큰 사용량을 실시간 모니터링할 수 있게 하였고, 용어집 및 검색 도구를 LangChain Tool로 구현하였다(+480라인).

테스트 인프라(`tests/` conftest.py, fixtures, 유틸리티)를 구축하고, Locust 부하 테스트 스크립트(80라인), prompt_loader 단위 테스트(72라인)를 포함한 다층 테스트 구조를 확립하였다. 팀 문서 20종(AI 파이프라인, 배포, Docker, 기여 가이드, AWS 인프라 11종 등 +1,712라인)을 작성하여 팀 운영 기반을 마련하였다.

### Result
- 커밋 14건, 코드 변경량 약 +5,200라인
- 테스트 계층 3층 구축: unit(프롬프트 검증) / backend(API 통합) / integration(E2E)
- PRD 상세화로 팀 전체 구현 방향 정렬, 불필요한 재작업 감소
- LangSmith 트레이싱으로 AI 에이전트 관측 가능성(observability) 확보
- Perplexity 수집기로 데이터 소스 다각화 (LLM 단독 생성 대비 사실 정확도 향상)
- 팀 문서 20종 작성으로 온보딩 시간 단축 및 운영 효율화

---

## Phase 2: 18노드 LangGraph 파이프라인 설계 및 구축 (02-12 ~ 02-13)

### Situation
기존 데이터 파이프라인은 레거시 스크립트 기반의 순차 실행 구조로, 뉴스/리서치 크롤링부터 LLM 큐레이션, 내러티브 생성, DB 저장까지의 전체 흐름이 단일 스크립트에 결합되어 있었다. 이 구조에서는 개별 노드의 테스트와 디버깅이 어렵고, 실행 중 한 단계의 실패가 전체 파이프라인을 중단시키는 문제가 있었다. 또한 3개 토픽(키워드 카드)을 생성하기 위해 파이프라인을 3번 순차 실행해야 하여 전체 처리 시간이 과도하게 길었다.

### Task
- 레거시 파이프라인을 18노드 LangGraph StateGraph로 재설계
- 데이터 수집 모듈 신규 개발 (뉴스 크롤러, 리서치 크롤러, 스크리너 등)
- DB 저장 레이어(writer.py) 구축 — asyncpg 직접 저장
- Pydantic v2 기반 파이프라인 스키마 정의
- 파이프라인 테스트 코드 작성

### Action
데이터 파이프라인을 18노드 LangGraph StateGraph로 전면 재설계하였다. 이 작업은 단일 커밋 기준 56개 파일, +4,870 / -829라인의 대규모 변경이었다. 파이프라인의 노드를 기능별로 분리하여 `nodes/` 디렉토리에 배치하였다: crawlers(뉴스/리서치 크롤링 131라인), screening(종목 스크리닝 87라인), curation(LLM 큐레이션 274라인), interface1(71라인), interface2(294라인), interface3(434라인), db_save(68라인).

데이터 수집 모듈을 `data_collection/` 디렉토리에 신규 개발하였다: news_crawler.py(215라인), research_crawler.py(319라인), screener.py(143라인), openai_curator.py(447라인), news_summarizer.py(275라인), intersection.py(26라인), attention 서브 모듈 3종(media 130라인, scoring 237라인, universe 106라인). 이들은 네이버 뉴스, 증권사 리서치, 종목 스크리닝 등 다양한 소스에서 데이터를 수집하고 LLM으로 큐레이션하는 역할을 수행한다.

asyncpg 기반 DB 저장 레이어(`writer.py`)를 구축하고, Pydantic v2 스키마(`schemas.py` 192라인)를 정의하여 파이프라인 데이터의 타입 안전성을 확보하였다. `llm_utils.py`(103라인)에 JSON 파싱 재시도 로직을 구현하여 LLM 응답의 포맷 오류에 대한 내성을 갖추었다. 프롬프트 템플릿 9종(page_purpose, historical_case, narrative_body, hallucination_check, final_hallucination, chart_generation, glossary_generation, _chart_skeletons, _tone_guide)을 신규 작성하고 기존 레거시 템플릿 9종을 삭제하여 완전히 교체하였다.

테스트 코드 3종(test_data_collection.py 215라인, test_data_collection_utils.py 235라인, test_nodes.py 169라인, test_schemas.py 94라인)을 작성하고, datapipeline 종합 가이드 문서(README.md 837라인)를 작성하였다.

### Result
- 커밋 3건(핵심), 코드 변경량 약 +6,600라인
- 18노드 LangGraph 파이프라인 아키텍처 완성: 크롤링 → 스크리닝 → 큐레이션 → 내러티브 생성 → DB 저장
- 데이터 수집 모듈 8종 신규 개발로 수집 소스 5개 이상 확보
- asyncpg DB 저장 + Pydantic v2 스키마로 타입 안전한 데이터 플로우 구축
- 파이프라인 테스트 4종으로 각 노드의 독립적 검증 가능

---

## Phase 3: 파이프라인 최적화 — 병렬화·안정화·멀티토픽 (02-13)

### Situation
18노드 파이프라인이 동작하기 시작하였으나, 전체 실행이 순차적으로 이루어져 3개 토픽 생성 시 처리 시간이 과도하게 길었다. Interface 3 단계에서 LLM 응답의 JSON이 max_tokens 제한으로 잘리는 문제가 빈번하게 발생하였고, DB 동시 쓰기 시 race condition으로 데이터 유실이 보고되었다. 프롬프트 템플릿의 모델 ID가 구버전으로 설정되어 있어 성능이 저하되고, chart_agent에서 한 섹션의 에러가 전체 파이프라인을 중단시키는 문제가 있었다.

### Task
- 파이프라인 3개 병렬 분기 적용 (처리 시간 단축)
- Interface 3 다단계 파이프라인 + chart_agent 통합
- Interface 3 프롬프트 9종 신규 추가 및 max_tokens 조정
- DB writer race condition 방지 (advisory lock + ON CONFLICT)
- 멀티토픽 루프 구현 (`--topic-count` 옵션)
- 프롬프트 모델 ID 업데이트 및 max_tokens 최적화
- Interface 3 병렬화 + 불필요한 hallcheck 제거

### Action
파이프라인에 3개 병렬 분기를 적용하여(`graph.py` +289라인, `run.py` +169라인) 독립적인 토픽 처리를 동시에 수행할 수 있게 하였다. 멀티토픽 루프를 구현하여(`--topic-count` CLI 옵션, curation +74라인, run.py +214라인) 한 번의 실행으로 3개 키워드 카드를 생성하는 워크플로우를 완성하였다.

Interface 3 단계를 다단계 파이프라인으로 재구성하고 chart_agent를 통합하였다(+724 / -264라인). 신규 프롬프트 템플릿 9종(3_pages, 3_theme, 3_glossary, 3_chart_generation, 3_chart_reasoning, 3_tone_final, 3_hallcheck_pages, 3_hallcheck_glossary, 3_hallcheck_chart, +814라인)을 추가하여 각 서브 단계별 LLM 호출을 세분화하였다. chart_agent에 per-section 에러 처리를 도입하여 개별 차트 생성 실패가 전체 파이프라인을 중단시키지 않도록 방어하였다.

DB writer에 PostgreSQL advisory lock과 ON CONFLICT 절을 추가하여 동시 쓰기 시 race condition을 방지하였다. briefing_stocks의 catalyst 필드 매핑과 키워드 누적 로직을 수정하여 데이터 정합성을 확보하였다(+386라인). 프롬프트 모델 ID를 최신 버전(claude-sonnet-4-5-20250929, gpt-5-mini)으로 업데이트하고, hallucination_check max_tokens를 8,192에서 16,384로, Interface 3 프롬프트를 16,000으로 증가시켜 JSON 잘림 문제를 해소하였다.

Interface 3 파이프라인 최적화에서는 서브 단계를 병렬화하고 중복 hallcheck를 제거하여 처리 시간을 단축하였다(+228 / -123라인). curate_topics의 source_id 검증을 완화하여 unknown 소스에 대해 경고만 출력하고 파이프라인을 계속 진행하도록 수정하였다. Pydantic v2 호환성 문제(model_dump_json → json.dumps)도 해결하였다.

### Result
- 커밋 17건, 코드 변경량 약 +2,600라인
- 3개 병렬 분기 + 멀티토픽 루프로 3카드 동시 생성 (순차 대비 약 2~3배 처리 속도 향상)
- Interface 3 프롬프트 9종 추가로 세분화된 LLM 파이프라인 구축
- advisory lock + ON CONFLICT로 DB 동시 쓰기 안정성 확보
- max_tokens 조정 + per-section 에러 처리로 파이프라인 중단율 대폭 감소
- JSON 잘림 문제 해소, 프롬프트 모델 최신화

---

## Phase 4: 프로덕션 안정화 — KST·타입 수정·Gemini 확장 (02-14 ~ 02-16)

### Situation
파이프라인이 프로덕션 환경에서 운영되기 시작하면서, 서버 타임존이 UTC인 환경에서 날짜 처리가 KST 기준으로 통일되지 않아 "어제의 브리핑"이 표시되는 문제가 발생하였다. asyncpg의 executemany 호출에서 Python 타입과 PostgreSQL 컬럼 타입의 불일치로 briefing_stocks 저장이 실패하는 버그가 보고되었다. 또한 OpenAI와 Claude에 집중된 LLM 의존도를 분산할 필요가 있었다.

### Task
- 전체 날짜 처리를 KST 기준으로 일괄 전환
- asyncpg executemany 타입 불일치 버그 수정
- Google Gemini 프로바이더 추가로 LLM 다각화
- LLM 모델 레퍼런스 문서 작성

### Action
날짜 처리 KST 일괄 적용 작업에서는 datapipeline의 `config.py`에 `KST` 타임존 상수와 `kst_today()` 헬퍼 함수를 추가하고, `writer.py`, `crawlers.py`, `curation.py`, `run.py` 등 파이프라인 전반의 `date.today()` / `datetime.now().date()` 호출을 `kst_today()`로 교체하였다(6개 파일, +171 / -143라인). FastAPI `briefing.py`의 오늘 날짜 조회 로직도 KST 기준으로 변경하여 파이프라인과 API 간 날짜 일관성을 확보하였다.

asyncpg executemany 타입 불일치 문제를 수정하였다. `writer.py`에서 briefing_stocks 저장 시 Python float → PostgreSQL numeric, str → text 등의 타입 캐스팅을 명시적으로 수행하여 executemany 호출의 안정성을 확보하였다(+16 / -11라인).

Google Gemini 프로바이더를 MultiProviderClient에 추가하여(+106라인) LLM 프로바이더를 4종(OpenAI, Perplexity, Claude, Gemini)으로 확장하였다. `config.py`에 Gemini API 키 설정을 추가하고, `prompt_loader.py`에 Gemini 프로바이더 분기를 구현하였다. LLM 모델 레퍼런스 문서(172라인)를 작성하여 각 프로바이더별 사용 가능한 모델, 토큰 제한, 비용을 정리하였다.

### Result
- 커밋 3건, 코드 변경량 약 +480라인
- KST 날짜 처리 일괄 적용으로 UTC 서버 환경에서의 날짜 불일치 해소
- asyncpg 타입 캐스팅 명시로 briefing_stocks 저장 안정성 확보
- Google Gemini 프로바이더 추가로 LLM 4종 운영 체계 구축 (비용 최적화 옵션 확보)
- LLM 모델 레퍼런스 문서로 팀 전체의 모델 선택 의사결정 지원

---

## 전체 요약

| 지표 | 수치 |
|------|------|
| 총 커밋 수 | 34건 (머지 커밋 포함) |
| 코드 변경량 | 약 +14,900 / -1,500라인 |
| 활동 기간 | 02-03 ~ 02-16 (14일) |
| LangGraph 파이프라인 노드 | 18개 |
| 데이터 수집 모듈 | 8종 (뉴스, 리서치, 스크리너, 큐레이터, 요약기, 교차분석, attention 3종) |
| 프롬프트 템플릿 | 18종 이상 (Interface 2: 9종 + Interface 3: 9종) |
| LLM 프로바이더 통합 | 4종 (OpenAI, Perplexity, Claude, Gemini) |
| 테스트 계층 | 3층 (unit / backend / integration) + 파이프라인 테스트 4종 |
| 팀 문서 | 20종 이상 |

QA 기반 구축에서 출발하여 18노드 LangGraph 파이프라인의 설계·구현·최적화·안정화까지 전 주기를 주도하였다. 테스트 프레임워크와 문서화를 통해 팀 전체의 품질 기준을 확립하고, 파이프라인 병렬화와 프롬프트 엔지니어링으로 프로덕션 수준의 콘텐츠 생성 시스템을 완성하였다.
