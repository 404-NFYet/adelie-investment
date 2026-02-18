# Datapipeline 최적화 8단계 결과 요약 (2026-02-18)

## 개요
- 목표: 생성 속도 개선 + API 사용량(호출/토큰) 절감 + 안정성 강화
- 범위: Interface2/3 LLM 파이프라인, 데이터수집 LLM 호출, 차트 에이전트, 재시도/동시성 정책, 테스트 가드레일

## 단계별 결과

### 1) 기준선 측정(Observability) 추가
- 적용:
  - `ai/llm_observability.py` 신규
  - `ai/llm_utils.py`, `run.py`에 호출/토큰/지연/이벤트 집계 연결
  - `data_collection/news_summarizer.py`, `data_collection/openai_curator.py`, `data_collection/research_crawler.py`에도 계측 연결
- 확인:
  - `mock` 실행 로그에서 `--- LLM 사용량 요약 ---` + `호출 없음` 확인 완료

### 2) max_tokens 상한 축소 (빠른 비용 절감)
- 조정:
  - `prompts/templates/3_chart_generation.md`: `16000 -> 7000`
  - `prompts/templates/3_chart_reasoning.md`: `8192 -> 2500`
  - `prompts/templates/3_hallcheck_chart.md`: `8192 -> 2500`
  - `prompts/templates/narrative_body.md`: `8192 -> 5000`
  - `prompts/templates/3_tone_final.md`: `8192 -> 5000`
  - `prompts/templates/hallucination_check.md`: `4096 -> 3000`
  - `prompts/templates/3_hallcheck_pages.md`: `16000 -> 6000`
- 확인:
  - 프롬프트 메타값 반영 확인 완료

### 3) 중복 호출 캐시
- 적용:
  - `ai/llm_response_cache.py` 신규 (TTL + max entries + LRU 정리)
  - `ai/llm_utils.py`에 cache hit/store 연결
  - 관측 이벤트 추가: `cache_hit`, `cache_store`
- 기본값:
  - `LLM_CACHE_ENABLED=true`
  - `LLM_CACHE_TTL_SECONDS=900`
  - `LLM_CACHE_MAX_ENTRIES=512`
- 확인:
  - 컴파일/로직 검증 완료

### 4) 모델 라우팅 분리(검증 단계 소형화)
- 변경:
  - `prompts/templates/hallucination_check.md`: `gpt-5.2 -> gpt-5-mini`
  - `prompts/templates/3_hallcheck_glossary.md`: `gpt-5.2 -> gpt-5-mini`
  - `prompts/templates/3_hallcheck_pages.md`: `gpt-5.2 -> gpt-5-mini`
- 비고:
  - `3_hallcheck_pages`는 현재 기본 그래프 경로에서 미사용(`merge_theme_pages` 대체)이나 fallback 대비 반영

### 5) 차트 파이프라인 사전 게이트 + 재시도 축소
- 적용 파일: `nodes/chart_agent.py`
- 핵심:
  - 생성 전 스킵 게이트 추가(요약 step, 비정량 hint, 데이터부족 문구 등)
  - 재시도 범위 축소: `step<=4 -> step<=3`
  - 재시도 tool call 상한 도입: `MAX_RETRY_TOOL_CALLS=4`
- 확인:
  - 함수 단위 스모크 테스트로 게이트 동작 확인 완료

### 6) 재시도 정책 정교화
- 적용 파일: `ai/llm_utils.py`
- 핵심:
  - OpenAI 재시도는 retryable error일 때만 수행
  - JSON 파싱 실패 시 로컬 복구(`_try_local_json_repair`) 우선
  - 3차 OpenAI JSON fallback은 핵심 프롬프트만 허용
- 설정:
  - `CRITICAL_JSON_PROMPTS` 환경변수로 3차 fallback 허용 prompt 제어
- 확인:
  - 로컬 복구/재시도 판별 스모크 테스트 통과

### 7) 동시성 상한 + Rate-limit 안정화
- 적용:
  - `ai/multi_provider_client.py`
    - 전역/프로바이더 세마포어
    - provider 재시도 + 지수 백오프(jitter)
    - timeout 설정
  - `nodes/chart_agent.py`
    - 섹션 병렬 상한 `CHART_AGENT_MAX_PARALLEL` 도입
- 기본값:
  - `LLM_MAX_CONCURRENCY=6`
  - `OPENAI_MAX_CONCURRENCY=4`
  - `PERPLEXITY_MAX_CONCURRENCY=2`
  - `ANTHROPIC_MAX_CONCURRENCY=2`
  - `PROVIDER_MAX_RETRIES=1`
  - `CHART_AGENT_MAX_PARALLEL=3`
- 확인:
  - 컴파일 및 상수 로딩 확인 완료

### 8) 품질/회귀 자동검증 가드레일
- 적용:
  - `tests/test_llm_observability_guardrails.py` 신규
  - `tests/test_llm_utils_json_retry.py` 강화
    - 캐시/집계 reset fixture
    - cache hit로 호출 수 감소 검증
    - 호출 수/토큰 상한 가드레일 검증
  - `ai/llm_response_cache.py`에 `reset_llm_cache()` 추가
- 실행 결과:
  - `python -m pytest -q -p no:cacheprovider tests/test_llm_utils_json_retry.py tests/test_llm_observability_guardrails.py`
  - `13 passed`

## 변경 파일 목록 (핵심)
- 신규:
  - `ai/llm_observability.py`
  - `ai/llm_response_cache.py`
  - `tests/test_llm_observability_guardrails.py`
- 수정:
  - `ai/llm_utils.py`
  - `ai/multi_provider_client.py`
  - `run.py`
  - `nodes/chart_agent.py`
  - `data_collection/news_summarizer.py`
  - `data_collection/openai_curator.py`
  - `data_collection/research_crawler.py`
  - `prompts/templates/3_chart_generation.md`
  - `prompts/templates/3_chart_reasoning.md`
  - `prompts/templates/3_hallcheck_chart.md`
  - `prompts/templates/3_hallcheck_glossary.md`
  - `prompts/templates/3_hallcheck_pages.md`
  - `prompts/templates/3_tone_final.md`
  - `prompts/templates/hallucination_check.md`
  - `prompts/templates/narrative_body.md`
  - `tests/test_llm_utils_json_retry.py`

## 운영 시 확인 포인트
- `LANGSMITH_TRACING_V2=false`로 검증 실행 시 외부 네트워크 경고/지연 최소화
- 새 로그 섹션(`LLM 사용량 요약`)으로 프롬프트별 비용 추이를 지속 모니터링
- `live` 1건 실행으로 토큰 절감률(기존 대비)을 최종 산출 권장
