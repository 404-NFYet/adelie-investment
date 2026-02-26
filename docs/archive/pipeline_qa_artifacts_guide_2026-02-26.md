# Pipeline QA 아티팩트 가이드

최종 수정일: 2026-02-26  
기준 브랜치: `dev-final/frontend`  
적용 코드 기준: `datapipeline/run.py`, `datapipeline/ai/llm_response_cache.py`, `datapipeline/graph.py`, `datapipeline/nodes/db_save.py`

---

## 1) 아티팩트가 뭐예요?

아티팩트(artifact)는 **실행 결과를 재현/검증할 수 있게 남기는 파일 묶음**입니다.

이 파이프라인에서는 QA 실행 1회(run)마다 아래를 남깁니다.
- 어떤 설정으로 돌렸는지
- 입력 샘플이 무엇이었는지
- 케이스별 품질/차트/가독성/토큰 지표가 어땠는지
- 실패가 어디서 왜 났는지
- 전체 요약 지표와 사람이 읽는 보고서

즉, “감으로 좋아졌다”가 아니라, **수치와 로그로 전/후 비교**할 수 있게 만드는 기록입니다.

---

## 2) 이번에 바뀐 핵심

### 2.1 CLI 플래그 추가 (내부 실행용)
`datapipeline/run.py`에 아래가 추가되었습니다.

- `--qa-run-id <id>`: 실행 ID 고정
- `--qa-log-dir <path>`: 아티팩트 저장 루트 변경
- `--no-db-save`: 측정 전용 모드 (DB 저장 스킵)
- `--emit-case-metrics-jsonl`: 케이스별 메트릭 JSONL 출력
- `--cache-bust`: 실행 전 캐시 초기화 (A/B 비교)

참고:
- QA 관련 플래그를 쓰고 `--topic-count`를 직접 안 주면, 기본 샘플 수는 12로 보정됩니다.

### 2.2 DB 저장 스킵 경로 추가
- `BriefingPipelineState`에 `no_db_save: bool` 추가 (`datapipeline/graph.py`)
- `save_to_db_node`에서 `no_db_save=true`면 저장하지 않고 `skipped` 처리 (`datapipeline/nodes/db_save.py`)

### 2.3 캐시 통계 스냅샷 추가
`datapipeline/ai/llm_response_cache.py`에 캐시 통계가 추가되었습니다.

- `hits`, `misses`, `hit_rate`
- `avg_age_s`, `ttl_s`, `max_entries`
- `enabled`, `entries`

이를 run 종료 시 `cache_stats.json`으로 저장합니다.

### 2.4 QA 아티팩트 8종 자동 생성
QA 모드에서 실행 종료 시 아래를 자동 생성합니다.

경로:
`docs/archive/pipeline-qa/<YYYY-MM-DD>/run_<run_id>/`

필수 파일:
1. `run_manifest.json`
2. `input_samples.jsonl`
3. `case_metrics.jsonl`
4. `llm_stats.json`
5. `cache_stats.json`
6. `failures.jsonl`
7. `summary_metrics.json`
8. `qa_report.md`

---

## 3) 파일별로 무엇이 들어가나요?

### 3.1 `run_manifest.json`
실행 메타 정보입니다.

주요 필드:
- `run_id`, `started_at_kst`, `ended_at_kst`
- `git_sha`, `branch`, `pipeline_source_ref` (현재 고정: `origin/dev-final/pipeline`)
- `mode` (`measurement_only` 또는 `normal`)
- `sample_size`
- `chart_policy` (현재 `2-4`)
- `quality_priority` (현재 `readability_first`)
- `cache_scope` (현재 `step1_summary_only`)
- `env_fingerprint` (민감값 원문 대신 hash/길이만 기록)

### 3.2 `input_samples.jsonl`
케이스별 입력 샘플 메타입니다.

주요 필드:
- `sample_id`
- `keyword`
- `category`
- `stock_codes`
- `briefing_id`, `briefing_date`

### 3.3 `case_metrics.jsonl`
핵심 품질 지표(케이스 단위)입니다.

주요 필드:
- 형식/호환: `json_parse_ok`, `schema_ok`, `frontend_render_ok`
- 가독성: `avg_sentence_len`, `long_sentence_ratio`
- 구조: `content_len_by_step`, `bullets_count_by_step`, `glossary_count_by_step`
- 차트: `chart_count_total`, `chart_steps`, `chart_types`, `chart_type_unique_count`, `chart_policy_ok`
- 위험: `hallucination_risk_max`, `hallucination_items_count`
- 비용: `prompt_tokens`, `completion_tokens`, `llm_elapsed_s`
- 캐시: `cache_hit_count`, `cache_store_count`

### 3.4 `llm_stats.json`
LLM 관측치 스냅샷입니다.

구성:
- `aggregate`: run 전체 누적
- `cases`: 케이스별 stats

### 3.5 `cache_stats.json`
LLM 캐시 지표입니다.

- `hits`, `misses`, `hit_rate`
- `avg_age_s`, `ttl_s`, `max_entries`

### 3.6 `failures.jsonl`
실패/경고 이벤트 로그입니다.

주요 필드:
- `sample_id`, `stage`, `error_code`, `message`, `raw_excerpt`, `stacktrace_hash`

현재 표준 코드:
- `FORMAT_JSON_FAIL`
- `SCHEMA_FAIL`
- `CHART_POLICY_FAIL`
- `READABILITY_FAIL`
- `RENDER_FAIL`
- `LLM_CALL_FAIL`

### 3.7 `summary_metrics.json`
run 전체 집계 요약입니다.

예:
- `success_rate`, `renderable_rate`
- `avg_chart_count`, `chart_policy_compliance_rate`
- `avg_sentence_len`, `avg_long_sentence_ratio`
- `prompt_tokens_total`, `completion_tokens_total`, `llm_elapsed_total_s`

### 3.8 `qa_report.md`
사람이 읽는 보고서입니다.

구성:
- Summary
- Top 5 Failure Types
- Chart over/under 케이스
- 난이도(가독성) 이슈 케이스
- 다음 실험 우선순위

---

## 4) 실행 예시

### 4.1 Baseline (기록 전용)
```bash
.venv/bin/python -m datapipeline.run \
  --backend live \
  --market KR \
  --topic-count 12 \
  --no-db-save \
  --emit-case-metrics-jsonl \
  --qa-run-id baseline_20260226
```

### 4.2 Repeatability (동일 조건 재실행)
```bash
.venv/bin/python -m datapipeline.run \
  --backend live \
  --market KR \
  --topic-count 12 \
  --no-db-save \
  --emit-case-metrics-jsonl \
  --qa-run-id repeat_20260226
```

### 4.3 Cache A/B
A (cache bust):
```bash
.venv/bin/python -m datapipeline.run \
  --backend live \
  --market KR \
  --topic-count 12 \
  --no-db-save \
  --emit-case-metrics-jsonl \
  --cache-bust \
  --qa-run-id cacheA_bust_20260226
```

B (cache 사용):
```bash
.venv/bin/python -m datapipeline.run \
  --backend live \
  --market KR \
  --topic-count 12 \
  --no-db-save \
  --emit-case-metrics-jsonl \
  --qa-run-id cacheB_cached_20260226
```

### 4.4 복붙용 1줄 커맨드
Baseline:
```bash
cd /home/ubuntu/adelie-investment && .venv/bin/python -m datapipeline.run --backend live --market KR --topic-count 12 --no-db-save --emit-case-metrics-jsonl --qa-run-id baseline_20260226
```

Repeatability:
```bash
cd /home/ubuntu/adelie-investment && .venv/bin/python -m datapipeline.run --backend live --market KR --topic-count 12 --no-db-save --emit-case-metrics-jsonl --qa-run-id repeat_20260226
```

Cache A (bust):
```bash
cd /home/ubuntu/adelie-investment && .venv/bin/python -m datapipeline.run --backend live --market KR --topic-count 12 --no-db-save --emit-case-metrics-jsonl --cache-bust --qa-run-id cacheA_bust_20260226
```

Cache B (cached):
```bash
cd /home/ubuntu/adelie-investment && .venv/bin/python -m datapipeline.run --backend live --market KR --topic-count 12 --no-db-save --emit-case-metrics-jsonl --qa-run-id cacheB_cached_20260226
```

---

## 5) 현재 정책값(코드 기준)

- 차트 정책: `2~4개` (`CHART_POLICY_MIN=2`, `CHART_POLICY_MAX=4`)
- 가독성 기준:
  - 평균 문장 길이 `<= 95`
  - 긴 문장 비율(`>=120자`) `<= 0.35`
- 시간 기록: KST
- API/토큰/URL secret는 마스킹 후 기록

---

## 6) smoke 실행 결과 (이미 생성됨)

샘플 실행 ID:
- `qa_smoke_20260226`

경로:
- `docs/archive/pipeline-qa/2026-02-26/run_qa_smoke_20260226/`

확인된 내용:
- 8개 필수 아티팩트 생성 완료
- `no_db_save` 모드에서 DB 저장 스킵 확인
- `summary_metrics.json`, `qa_report.md` 자동 생성 확인

---

## 7) 주의사항

- `--backend mock` 실행은 LLM 토큰 지표가 0일 수 있습니다.
- 현재 topic 1 생성 결과의 `curated_topics` 개수에 따라 후속 topic 생성이 생략될 수 있습니다.
- LangSmith 쪽 `run_type=agent` 경고는 본 QA 아티팩트 생성과는 별개입니다.

---

## 8) 실제 Baseline 실행 진단 (2026-02-26)

### 8.1 1차 실행 결과
실행:
```bash
.venv/bin/python -m datapipeline.run --backend live --market KR --topic-count 12 --no-db-save --emit-case-metrics-jsonl --qa-run-id baseline_20260226
```

결과:
- `run_baseline_20260226` 아티팩트 생성됨
- 시작 직후 `sample_001`에서 실패

주요 실패 원인:
1. `feedparser` 미설치 (`No module named 'feedparser'`)
2. `datapipeline/data/research/*` 경로 쓰기 권한 없음 (`Permission denied`)

증거:
- `failures.jsonl`에 `LLM_CALL_FAIL` 기록
- 콘솔 로그에 `No module named 'feedparser'`, `Permission denied` 확인

### 8.2 환경 복구 조치
실행한 조치:
```bash
.venv/bin/python -m pip install feedparser
sudo -n chown -R ubuntu:ubuntu datapipeline/data/research datapipeline/data/news
```

### 8.3 재실행 진단
재실행에서 확인된 병목:
- 데이터 수집 완료 후 `summarize_news` 단계에서 장시간 대기
- 로그 기준: `627건 → 11 청크(Map/Reduce)` 처리
- `summarize_research`는 빠르게 완료되나, `summarize_news`가 전체 런타임을 지배

관련 코드 단서:
- `datapipeline/data_collection/news_summarizer.py`
  - 청크 요약 API 타임아웃 `timeout=90`
  - 청크 수가 많아지면 누적 지연이 크게 증가

### 8.4 현재 결론
지금 품질 QA를 막는 1순위는 **모델 품질 이슈가 아니라 실행 파이프라인 병목/환경 안정성**입니다.

핵심 리스크 우선순위:
1. 환경 의존성 누락 (`feedparser`)
2. 실행 계정/파일 권한 불일치
3. 뉴스 요약 단계 과도한 처리량(627건, 11청크)으로 인한 장기 지연

### 8.5 다음 액션 (권장)
1. Baseline 측정 안정화용으로 요약 입력 상한(예: 뉴스 상위 N건) 적용
2. `summarize_news` 단계에 hard timeout + 부분 성공 저장 정책 추가
3. 완료 가능한 샘플 수(예: 3~5)로 1차 품질 지표 확보 후 12개 확장
