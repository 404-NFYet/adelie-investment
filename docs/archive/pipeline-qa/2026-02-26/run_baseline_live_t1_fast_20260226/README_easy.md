# Pipeline QA 쉬운 요약

기준 런: `baseline_live_t1_fast_20260226`  
기준 시각(KST): `2026-02-26 23:17:13`

---

## 1) 한 줄 결론
- **파이프라인는 끝까지 돌았고 포맷은 정상**이지만, **차트는 0개**라서 현재 프론트 차트 품질 요구(2~4개)를 만족하지 못했습니다.

---

## 2) 이번 실행에서 확인된 핵심 숫자
- `success_rate`: `1.0` (실행 자체는 성공)
- `renderable_rate`: `1.0` (JSON/스키마/렌더 호환은 정상)
- `avg_chart_count`: `0.0` (차트 없음)
- `chart_policy_compliance_rate`: `0.0` (정책 미준수)
- `총 소요시간`: 약 `1011초` (약 16분 51초)
- `LLM 토큰`: prompt `133,765`, completion `38,383`

상세 원본:
- [summary_metrics.json](/home/ubuntu/adelie-investment/docs/archive/pipeline-qa/2026-02-26/run_baseline_live_t1_fast_20260226/summary_metrics.json)
- [case_metrics.jsonl](/home/ubuntu/adelie-investment/docs/archive/pipeline-qa/2026-02-26/run_baseline_live_t1_fast_20260226/case_metrics.jsonl)

---

## 3) 왜 차트가 0개였나?
직접 원인은 **차트 툴 호출 오류**입니다.

실행 로그에서 반복 확인:
- `StructuredTool object is not callable`

영향:
- 차트 reasoning 단계는 돌았지만,
- 실제 툴 실행이 실패해서 chart generation이 빈 결과로 끝났고,
- 최종 결과에 차트가 하나도 들어가지 않았습니다.

코드 위치:
- [chart_agent.py:319](/home/ubuntu/adelie-investment/datapipeline/nodes/chart_agent.py:319)

---

## 4) 왜 오래 걸렸나?
가장 큰 병목은 아래 3개입니다.

1. `run_glossary`: `314.76s`
- 용어를 많이 뽑고(이번 케이스 21개), Perplexity를 용어별로 순차 호출해서 지연 누적

2. `run_tone_final`: `119.68s`
- 후반 단일 LLM 호출 시간이 큼

3. `validate_interface2`: `100.45s`
- hallucination check 호출이 길게 걸림

참고:
- 뉴스 요약은 상한 적용이 정상 동작함 (`630건 -> 80건`)

---

## 5) 좋은 점 (유지해야 하는 부분)
- `json_parse_ok=true`
- `schema_ok=true`
- `frontend_render_ok=true`
- 가독성 수치 양호:
  - `avg_sentence_len=43.17`
  - `long_sentence_ratio=0.0286`

즉, **문서 구조/렌더 계약은 안정적**입니다.

---

## 6) 다음 액션 (우선순위)
1. **차트 툴 호출 버그 먼저 수정**
- `StructuredTool` 호출 방식을 `.invoke/.ainvoke`로 수정
- 목표: 차트 개수 `0 -> 2~4`

2. **글로서리 검색 fan-out 줄이기**
- 용어 수 상한(예: 8~12)
- 중복 제거 강화
- 제한 병렬(예: 3개 동시) + timeout

3. **후반 LLM 단계 타임박스**
- `tone_final`, `validate_interface2` timeout/partial fallback 정의

---

## 7) 다시 실행할 때(복붙)
```bash
cd /home/ubuntu/adelie-investment && timeout 1800 env OPENAI_PHASE1_MAX_ITEMS_PER_KIND=80 OPENAI_PHASE1_MAP_REDUCE_BUDGET_S=180 OPENAI_PHASE1_REQUEST_TIMEOUT_S=45 .venv/bin/python -m datapipeline.run --backend live --market KR --topic-count 1 --no-db-save --emit-case-metrics-jsonl --qa-run-id baseline_live_t1_fast_20260226
```

