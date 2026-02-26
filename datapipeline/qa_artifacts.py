"""Pipeline QA 아티팩트 기록 유틸.

런 단위 아티팩트(8종)를 생성해 실행 품질을 비교 가능하게 만든다.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))

ERROR_CODES = {
    "FORMAT_JSON_FAIL",
    "SCHEMA_FAIL",
    "CHART_POLICY_FAIL",
    "READABILITY_FAIL",
    "RENDER_FAIL",
    "LLM_CALL_FAIL",
}


def kst_now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def kst_today_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _safe_git(cmd: list[str], default: str = "unknown") -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        return out or default
    except Exception:
        return default


def _mask_sensitive_text(text: str) -> str:
    masked = text
    masked = re.sub(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", "***@***", masked)
    masked = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*([^\s,]+)", r"\1=[REDACTED]", masked)
    masked = re.sub(r"([?&](?:token|key|secret|sig|signature)=)[^&]+", r"\1[REDACTED]", masked, flags=re.I)
    return masked


def _fingerprint_secret(name: str) -> dict[str, Any]:
    value = os.getenv(name)
    if not value:
        return {"set": False}
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return {
        "set": True,
        "sha256_12": digest,
        "length": len(value),
    }


def build_env_fingerprint() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "cache_enabled": os.getenv("LLM_CACHE_ENABLED", "true"),
        "cache_ttl_s": os.getenv("LLM_CACHE_TTL_SECONDS", "900"),
        "cache_max_entries": os.getenv("LLM_CACHE_MAX_ENTRIES", "512"),
        "OPENAI_API_KEY": _fingerprint_secret("OPENAI_API_KEY"),
        "CLAUDE_API_KEY": _fingerprint_secret("CLAUDE_API_KEY"),
        "PERPLEXITY_API_KEY": _fingerprint_secret("PERPLEXITY_API_KEY"),
        "DATABASE_URL": _fingerprint_secret("DATABASE_URL"),
        "REDIS_URL": _fingerprint_secret("REDIS_URL"),
        "LANGCHAIN_API_KEY": _fingerprint_secret("LANGCHAIN_API_KEY"),
        "LANGSMITH_API_KEY": _fingerprint_secret("LANGSMITH_API_KEY"),
    }


def _to_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _extract_sentences(text: str) -> list[str]:
    rough = re.split(r"[.!?。！？]\s+|\n+", str(text or ""))
    return [s.strip() for s in rough if len(s.strip()) >= 2]


def _risk_to_score(risk: str) -> int:
    table = {
        "낮음": 1,
        "low": 1,
        "중간": 2,
        "medium": 2,
        "보통": 2,
        "높음": 3,
        "high": 3,
    }
    return table.get(str(risk or "").strip().lower(), 0)


def map_error_code(stage: str, message: str) -> str:
    lower = f"{stage} {message}".lower()
    if "json" in lower and ("parse" in lower or "decode" in lower or "invalid" in lower):
        return "FORMAT_JSON_FAIL"
    if "schema" in lower or "validation" in lower or "pydantic" in lower:
        return "SCHEMA_FAIL"
    if "chart" in lower and ("policy" in lower or "2-4" in lower):
        return "CHART_POLICY_FAIL"
    if "readability" in lower or "long sentence" in lower:
        return "READABILITY_FAIL"
    if "render" in lower:
        return "RENDER_FAIL"
    return "LLM_CALL_FAIL"


def _sum_event_count(llm_stats: dict[str, Any], event_name: str) -> int:
    total = 0
    for bucket in (llm_stats.get("by_prompt") or {}).values():
        events = bucket.get("events") or {}
        total += int(events.get(event_name, 0) or 0)
    return total


def _extract_chart_types(chart_obj: dict[str, Any]) -> list[str]:
    types: list[str] = []
    data = chart_obj.get("data")
    if not isinstance(data, list):
        return types
    for trace in data:
        if isinstance(trace, dict):
            t = str(trace.get("type") or "unknown").strip()
            if t:
                types.append(t)
    return types


def build_case_metrics(
    *,
    sample_id: str,
    final_state: dict[str, Any],
    llm_stats: dict[str, Any],
) -> dict[str, Any]:
    output = final_state.get("full_output") or {}
    final_briefing = (output.get("interface_3_final_briefing") or {}) if isinstance(output, dict) else {}
    pages = final_briefing.get("pages") or []
    pages = pages if isinstance(pages, list) else []

    content_len_by_step: dict[str, int] = {}
    bullets_count_by_step: dict[str, int] = {}
    glossary_count_by_step: dict[str, int] = {}
    all_sentences: list[str] = []
    chart_steps: list[int] = []
    chart_types: list[str] = []

    for page in pages:
        if not isinstance(page, dict):
            continue
        step = str(page.get("step", ""))
        content = str(page.get("content") or "")
        bullets = page.get("bullets") if isinstance(page.get("bullets"), list) else []
        glossary = page.get("glossary") if isinstance(page.get("glossary"), list) else []
        content_len_by_step[step] = len(content)
        bullets_count_by_step[step] = len(bullets)
        glossary_count_by_step[step] = len(glossary)
        all_sentences.extend(_extract_sentences(content))

        chart = page.get("chart")
        if isinstance(chart, dict) and isinstance(chart.get("data"), list) and len(chart.get("data")) > 0:
            try:
                chart_steps.append(int(page.get("step")))
            except Exception:
                pass
            chart_types.extend(_extract_chart_types(chart))

    sentence_lengths = [len(s) for s in all_sentences]
    avg_sentence_len = round(sum(sentence_lengths) / len(sentence_lengths), 2) if sentence_lengths else 0.0
    long_sentence_ratio = (
        round(sum(1 for n in sentence_lengths if n >= 120) / len(sentence_lengths), 4)
        if sentence_lengths else 0.0
    )

    hallucination_items = final_briefing.get("hallucination_checklist") or []
    hallucination_items = hallucination_items if isinstance(hallucination_items, list) else []
    hallucination_risk_max = 0
    for item in hallucination_items:
        if isinstance(item, dict):
            hallucination_risk_max = max(hallucination_risk_max, _risk_to_score(str(item.get("risk") or "")))

    totals = llm_stats.get("totals") or {}
    chart_count_total = len(chart_steps)
    chart_type_unique_count = len(set(chart_types))
    chart_policy_ok = 2 <= chart_count_total <= 4
    frontend_render_ok = len(pages) > 0 and all(isinstance(p, dict) and p.get("content") for p in pages)
    schema_ok = bool(output)
    json_parse_ok = not bool(final_state.get("error"))

    return {
        "timestamp_kst": kst_now_iso(),
        "sample_id": sample_id,
        "json_parse_ok": json_parse_ok,
        "schema_ok": schema_ok,
        "frontend_render_ok": frontend_render_ok,
        "avg_sentence_len": avg_sentence_len,
        "long_sentence_ratio": long_sentence_ratio,
        "content_len_by_step": content_len_by_step,
        "bullets_count_by_step": bullets_count_by_step,
        "glossary_count_by_step": glossary_count_by_step,
        "chart_count_total": chart_count_total,
        "chart_steps": chart_steps,
        "chart_types": chart_types,
        "chart_type_unique_count": chart_type_unique_count,
        "chart_policy_ok": chart_policy_ok,
        "hallucination_risk_max": hallucination_risk_max,
        "hallucination_items_count": len(hallucination_items),
        "prompt_tokens": int(totals.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(totals.get("completion_tokens", 0) or 0),
        "llm_elapsed_s": float(totals.get("elapsed_s", 0.0) or 0.0),
        "cache_hit_count": _sum_event_count(llm_stats, "cache_hit"),
        "cache_store_count": _sum_event_count(llm_stats, "cache_store"),
    }


def build_input_sample(sample_id: str, topic: dict[str, Any]) -> dict[str, Any]:
    context = topic.get("interface_1_curated_context", topic) if isinstance(topic, dict) else {}
    stocks = context.get("selected_stocks") if isinstance(context, dict) else []
    stock_codes: list[str] = []
    if isinstance(stocks, list):
        for st in stocks:
            if isinstance(st, dict):
                code = st.get("ticker") or st.get("symbol")
                if code:
                    stock_codes.append(str(code))
    return {
        "sample_id": sample_id,
        "keyword": str(topic.get("topic") or context.get("theme") or ""),
        "category": str(topic.get("category") or ""),
        "stock_codes": stock_codes,
        "briefing_id": topic.get("briefing_id"),
        "briefing_date": context.get("date"),
    }


def build_summary_metrics(
    *,
    sample_size: int,
    case_metrics: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    attempted = len(case_metrics)
    if attempted > 0:
        success_n = sum(1 for x in case_metrics if x.get("json_parse_ok") and x.get("schema_ok"))
        render_n = sum(1 for x in case_metrics if x.get("frontend_render_ok"))
        policy_n = sum(1 for x in case_metrics if x.get("chart_policy_ok"))
        avg_chart_count = round(sum(float(x.get("chart_count_total", 0) or 0) for x in case_metrics) / attempted, 3)
        avg_sentence_len = round(sum(float(x.get("avg_sentence_len", 0.0) or 0.0) for x in case_metrics) / attempted, 3)
        avg_long_sentence_ratio = round(sum(float(x.get("long_sentence_ratio", 0.0) or 0.0) for x in case_metrics) / attempted, 4)
        prompt_tokens_total = int(sum(int(x.get("prompt_tokens", 0) or 0) for x in case_metrics))
        completion_tokens_total = int(sum(int(x.get("completion_tokens", 0) or 0) for x in case_metrics))
        llm_elapsed_total_s = round(sum(float(x.get("llm_elapsed_s", 0.0) or 0.0) for x in case_metrics), 4)
    else:
        success_n = render_n = policy_n = 0
        avg_chart_count = avg_sentence_len = avg_long_sentence_ratio = 0.0
        prompt_tokens_total = completion_tokens_total = 0
        llm_elapsed_total_s = 0.0

    failure_by_code = Counter()
    for f in failures:
        code = str(f.get("error_code") or "LLM_CALL_FAIL")
        if code not in ERROR_CODES:
            code = "LLM_CALL_FAIL"
        failure_by_code[code] += 1

    denom = float(max(sample_size, 1))
    return {
        "sample_size": sample_size,
        "cases_attempted": attempted,
        "success_rate": round(success_n / denom, 4),
        "renderable_rate": round(render_n / denom, 4),
        "avg_chart_count": avg_chart_count,
        "chart_policy_compliance_rate": round(policy_n / denom, 4),
        "avg_sentence_len": avg_sentence_len,
        "avg_long_sentence_ratio": avg_long_sentence_ratio,
        "prompt_tokens_total": prompt_tokens_total,
        "completion_tokens_total": completion_tokens_total,
        "llm_elapsed_total_s": llm_elapsed_total_s,
        "failure_count": len(failures),
        "failure_by_code": dict(failure_by_code),
    }


def build_qa_report(
    *,
    run_id: str,
    summary: dict[str, Any],
    case_metrics: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append(f"# Pipeline QA Report ({run_id})")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- cases_attempted: {summary.get('cases_attempted', 0)}")
    lines.append(f"- success_rate: {summary.get('success_rate', 0)}")
    lines.append(f"- renderable_rate: {summary.get('renderable_rate', 0)}")
    lines.append(f"- avg_chart_count: {summary.get('avg_chart_count', 0)}")
    lines.append(f"- chart_policy_compliance_rate: {summary.get('chart_policy_compliance_rate', 0)}")
    lines.append(f"- avg_sentence_len: {summary.get('avg_sentence_len', 0)}")
    lines.append(f"- avg_long_sentence_ratio: {summary.get('avg_long_sentence_ratio', 0)}")
    lines.append("")

    lines.append("## Top 5 Failure Types")
    failure_counts = Counter(str(f.get("error_code") or "LLM_CALL_FAIL") for f in failures)
    if failure_counts:
        for code, cnt in failure_counts.most_common(5):
            lines.append(f"- {code}: {cnt}")
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("## Chart Over/Under Cases")
    chart_outliers = [m for m in case_metrics if not m.get("chart_policy_ok")]
    if chart_outliers:
        for m in chart_outliers[:10]:
            lines.append(
                f"- {m.get('sample_id')}: chart_count={m.get('chart_count_total')} chart_steps={m.get('chart_steps')}"
            )
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("## Hard-to-Read Cases")
    hard_cases = [m for m in case_metrics if float(m.get("avg_sentence_len", 0)) > 95 or float(m.get("long_sentence_ratio", 0)) > 0.35]
    if hard_cases:
        for m in hard_cases[:10]:
            lines.append(
                f"- {m.get('sample_id')}: avg_sentence_len={m.get('avg_sentence_len')} long_sentence_ratio={m.get('long_sentence_ratio')}"
            )
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("## Next Experiment Priorities")
    if failure_counts:
        top_code = failure_counts.most_common(1)[0][0]
        lines.append(f"1. 최빈 실패 코드({top_code}) 재현/완화 실험")
    else:
        lines.append("1. 캐시 A/B로 토큰/지연 개선 폭 검증")
    lines.append("2. 차트 정책(2~4개) 편차 케이스 프롬프트 보정")
    lines.append("3. 가독성 지표 초과 케이스 문장 단순화 실험")
    return "\n".join(lines).strip() + "\n"


@dataclass
class QARunArtifacts:
    run_id: str
    sample_size: int
    qa_log_dir: Path
    pipeline_source_ref: str = "origin/dev-final/pipeline"
    chart_policy: str = "2-4"
    quality_priority: str = "readability_first"
    cache_scope: str = "step1_summary_only"
    started_at_kst: str = field(default_factory=kst_now_iso)
    run_dir: Path = field(init=False)
    input_samples: list[dict[str, Any]] = field(default_factory=list)
    case_metrics: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    llm_stats_cases: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.run_dir = self.qa_log_dir / kst_today_str() / f"run_{self.run_id}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.write_manifest(exit_code=None)

    def write_manifest(self, exit_code: int | None, ended_at_kst: str | None = None) -> None:
        manifest = {
            "run_id": self.run_id,
            "started_at_kst": self.started_at_kst,
            "ended_at_kst": ended_at_kst or self.started_at_kst,
            "git_sha": _safe_git(["git", "rev-parse", "HEAD"]),
            "branch": _safe_git(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
            "pipeline_source_ref": self.pipeline_source_ref,
            "mode": "measurement_only",
            "sample_size": self.sample_size,
            "chart_policy": self.chart_policy,
            "quality_priority": self.quality_priority,
            "cache_scope": self.cache_scope,
            "env_fingerprint": build_env_fingerprint(),
            "cases_attempted": len(self.case_metrics),
            "failures_count": len(self.failures),
            "exit_code": exit_code,
        }
        (self.run_dir / "run_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def record_input_sample(self, payload: dict[str, Any]) -> None:
        self.input_samples.append(payload)

    def record_case_metrics(self, payload: dict[str, Any]) -> None:
        self.case_metrics.append(payload)

    def record_failure(self, payload: dict[str, Any]) -> None:
        code = str(payload.get("error_code") or "LLM_CALL_FAIL")
        if code not in ERROR_CODES:
            payload["error_code"] = "LLM_CALL_FAIL"
        payload["timestamp_kst"] = payload.get("timestamp_kst") or kst_now_iso()
        payload["message"] = _mask_sensitive_text(str(payload.get("message") or ""))
        payload["raw_excerpt"] = _mask_sensitive_text(str(payload.get("raw_excerpt") or ""))
        self.failures.append(payload)

    def record_llm_case_stats(self, sample_id: str, stats: dict[str, Any]) -> None:
        self.llm_stats_cases.append({"sample_id": sample_id, "stats": stats})

    def finalize(self, cache_stats: dict[str, Any], exit_code: int) -> None:
        # input_samples.jsonl
        with (self.run_dir / "input_samples.jsonl").open("w", encoding="utf-8") as f:
            for row in self.input_samples:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # case_metrics.jsonl
        with (self.run_dir / "case_metrics.jsonl").open("w", encoding="utf-8") as f:
            for row in self.case_metrics:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # failures.jsonl
        with (self.run_dir / "failures.jsonl").open("w", encoding="utf-8") as f:
            for row in self.failures:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # llm_stats.json
        aggregate = {
            "totals": {
                "calls": sum(int((c.get("stats") or {}).get("totals", {}).get("calls", 0) or 0) for c in self.llm_stats_cases),
                "prompt_tokens": sum(int((c.get("stats") or {}).get("totals", {}).get("prompt_tokens", 0) or 0) for c in self.llm_stats_cases),
                "completion_tokens": sum(int((c.get("stats") or {}).get("totals", {}).get("completion_tokens", 0) or 0) for c in self.llm_stats_cases),
                "elapsed_s": round(sum(float((c.get("stats") or {}).get("totals", {}).get("elapsed_s", 0.0) or 0.0) for c in self.llm_stats_cases), 4),
            }
        }
        (self.run_dir / "llm_stats.json").write_text(
            json.dumps({"aggregate": aggregate, "cases": self.llm_stats_cases}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # cache_stats.json
        (self.run_dir / "cache_stats.json").write_text(
            json.dumps(cache_stats or {}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # summary_metrics.json
        summary = build_summary_metrics(
            sample_size=self.sample_size,
            case_metrics=self.case_metrics,
            failures=self.failures,
        )
        (self.run_dir / "summary_metrics.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # qa_report.md
        report = build_qa_report(
            run_id=self.run_id,
            summary=summary,
            case_metrics=self.case_metrics,
            failures=self.failures,
        )
        (self.run_dir / "qa_report.md").write_text(report, encoding="utf-8")

        self.write_manifest(exit_code=exit_code, ended_at_kst=kst_now_iso())
