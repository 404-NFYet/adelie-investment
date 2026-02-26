# Baseline Diagnosis (baseline_live_t1_fast_20260226)

## Run Snapshot
- date: 2026-02-26 (KST)
- sample_size: 1
- total_elapsed: 1011.08s
- prompt_tokens: 133,765
- completion_tokens: 38,383
- llm_elapsed_total_s: 734.0945

## Key Findings
1. Chart rendering failed functionally.
- symptom: `chart_count_total=0` (policy target 2~4 not met)
- direct error in runtime log:
  - `Tool get_corp_financials failed: 'StructuredTool' object is not callable`
  - `Tool search_web_for_chart_data failed: 'StructuredTool' object is not callable`
- impact:
  - chart reasoning ran for 4 sections (`background/concept/history/application`)
  - generation returned empty for all chart sections

2. Glossary pipeline is the dominant latency bottleneck.
- node elapsed:
  - `run_glossary: 314.76s`
  - `run_hallcheck_glossary: 74.27s`
- root cause pattern:
  - glossary term extraction produced 21 terms
  - Perplexity web search executed sequentially per term
  - several requests took ~27~31s each

3. Tone synthesis latency is high.
- `run_tone_final: 119.68s`
- single Anthropic call dominates end-stage latency

4. Data collection phase stabilized with limits.
- news crawl still large (`630` items), but summarize phase used cap:
  - `phase1_news_map` recorded `input_truncated=1`
  - configured cap applied: `630 -> 80`
- summarize times improved to manageable range:
  - `summarize_news: 48.23s`
  - `summarize_research: 46.91s`

## Quality Signals
- readability:
  - `avg_sentence_len=43.17`
  - `long_sentence_ratio=0.0286`
  - readability is acceptable in this sample.
- schema/render compatibility:
  - `json_parse_ok=true`, `schema_ok=true`, `frontend_render_ok=true`
  - format contract itself is stable.

## Immediate Next Actions
1. Fix chart tool invocation path in chart agent.
- replace direct callable usage for `StructuredTool` with `.invoke(...)`/`.ainvoke(...)` path.
- add hard guard: if tool execution error ratio exceeds threshold, fallback chart should still include minimal valid traces.

2. Reduce glossary search fan-out.
- cap extracted terms (e.g., top 8~12 by importance).
- deduplicate aggressively before search.
- parallelize bounded batches (e.g., 3-way) with per-request timeout.

3. Separate quality from enrichment.
- when glossary external search is slow, continue with local-only glossary synthesis and mark enrichment as partial.
- keep `qa_report` and `case_metrics` emitting even under partial completion.
