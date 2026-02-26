# 차트 생성 개선 전/후 비교 (쉬운 설명)

## 1) 한 줄 결론
- **툴 호출 오류는 해결됐지만, 차트 개수는 아직 0개**예요.
- 즉, "아예 못 그리는 버그"는 고쳤고, 이제는 "그릴지 말지 판단 로직"을 더 완화/보강해야 해요.

## 2) 이번에 바꾼 것
- 파일: `datapipeline/nodes/chart_agent.py`
1. `StructuredTool` 실행 방식 수정
   - 기존: 함수처럼 직접 호출하다가 `StructuredTool object is not callable` 에러 발생
   - 변경: `invoke(args)` 우선 호출, 없으면 기존 callable 호출
2. 차트 팩트체크 게이트 완화
   - 기존: 위험도 `중간/높음`이면 차트 숨김
   - 변경: 위험도 `높음`만 숨김, `중간`은 경고만 남기고 유지

## 3) 수치 비교 (Baseline vs After)

기준 실행
- Before: `run_baseline_live_t1_fast_20260226`
- After: `run_after_fix_live_t1_fast_20260226`

| 지표 | Before | After | 변화 |
|---|---:|---:|---:|
| success_rate | 1.0 | 1.0 | 동일 |
| renderable_rate | 1.0 | 1.0 | 동일 |
| avg_chart_count | 0.0 | 0.0 | 동일 (개선 없음) |
| chart_policy_compliance_rate | 0.0 | 0.0 | 동일 |
| avg_sentence_len | 43.17 | 44.4 | +1.23 |
| avg_long_sentence_ratio | 0.0286 | 0.0286 | 동일 |
| prompt_tokens_total | 133,765 | 149,845 | +16,080 (+12.0%) |
| completion_tokens_total | 38,383 | 38,134 | -249 (-0.65%) |
| llm_elapsed_total_s | 734.09s | 713.47s | -20.62s (-2.81%) |

추가 확인
- `3_chart_generation` 호출 수: **4 -> 6** (재시도/추가 시도 증가)
- `StructuredTool is not callable` 에러는 재실행 로그에서 **미발생**

## 4) 왜 아직 차트가 0개일까?
쉽게 말하면,
1. "데이터 가져오는 단계"는 좋아졌는데,
2. "최종으로 차트를 채택하는 단계"가 여전히 보수적이라
3. 결과적으로 빈 차트(null)로 끝나요.

즉, 지금 병목은 **툴 호출 실패**가 아니라 **생성/채택 정책**이에요.

## 5) 다음 개선안 (우선순위)
1. **P0: 강제 최소 차트 fallback 추가**
   - Step 1~4에서 차트가 비면, 내부 확정값(`selected_stocks.change_pct`, `attention_score`)으로 기본 bar/line 1개를 자동 생성
2. **P1: chart_generation 프롬프트 정책 조정**
   - "정합성 낮으면 null" 규칙을 완화하고, 근거가 부분적으로라도 있으면 단순 차트 우선 생성
3. **P1: 차트 채택 스코어러 도입**
   - 완전 차단 대신 점수화(근거 충분/중간/약함)해서 `약함`은 경고 라벨과 함께 노출
4. **P2: 가독성 후처리 자동화**
   - 문장 길이가 기준 초과면 자동 단문 리라이트(현재는 측정만 하고 보정은 없음)

## 6) 같은 방식으로 다시 실행하는 명령어
```bash
.venv/bin/python -m datapipeline.run \
  --backend live \
  --topic-count 1 \
  --qa-run-id after_fix_live_t1_fast_20260226 \
  --no-db-save \
  --emit-case-metrics-jsonl
```
