"""데이터 파이프라인 CLI 진입점.

사용법:
    # 실시간 데이터 수집 → 3개 카드 생성 (기본)
    python -m datapipeline.run --backend live --market KR

    # 카드 수 지정
    python -m datapipeline.run --backend live --topic-count 5

    # curated context JSON 파일 로드 → 내러티브 + 조립만
    python -m datapipeline.run --input path/to/curated.json --backend live

    # mock 테스트 (LLM 호출 없이 구조 검증)
    python -m datapipeline.run --backend mock --topic-count 3

    # 특정 토픽 인덱스 지정 (topics[] 배열이 있는 입력)
    python -m datapipeline.run --input output/curated_ALL.json --topic-index 0
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

from .ai.llm_observability import reset_llm_stats, snapshot_llm_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("datapipeline.run")

# output 디렉토리
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="데이터 파이프라인: 데이터 수집부터 최종 브리핑 JSON 생성까지",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="curated context JSON 경로. 생략하면 실시간 데이터 수집 모드",
    )
    parser.add_argument(
        "--backend",
        choices=["live", "mock", "auto"],
        default="auto",
        help="실행 백엔드. live=실제 API, mock=더미 응답, auto=API 키 유무로 결정",
    )
    parser.add_argument(
        "--market",
        choices=["KR", "US", "ALL"],
        default="KR",
        help="시장 선택 (데이터 수집 모드에서 사용, 기본: KR)",
    )
    parser.add_argument(
        "--topic-index",
        type=int,
        default=0,
        help="topics[] 배열에서 처리할 토픽 인덱스 (기본: 0)",
    )
    parser.add_argument(
        "--topic-count",
        type=int,
        default=3,
        help="생성할 카드(토픽) 수 (기본: 3)",
    )
    return parser.parse_args()


def pick_backend(arg_backend: str) -> str:
    """auto 모드에서 API 키 유무로 백엔드 결정."""
    if arg_backend != "auto":
        return arg_backend

    from .config import ANTHROPIC_API_KEY, OPENAI_API_KEY
    if ANTHROPIC_API_KEY or OPENAI_API_KEY:
        return "live"
    return "mock"


def _build_initial_state(
    *,
    input_path: str | None,
    topic_index: int,
    backend: str,
    market: str,
) -> dict:
    """파이프라인 초기 상태를 생성."""
    return {
        # 입력
        "input_path": input_path,
        "topic_index": topic_index,
        "backend": backend,
        "market": market,
        # Data Collection 중간 결과
        "raw_news": None,
        "raw_reports": None,
        "crawl_news_status": None,
        "crawl_research_status": None,
        "screened_stocks": None,
        "matched_stocks": None,
        "news_summary": None,
        "research_summary": None,
        "curated_topics": None,
        "websearch_log": None,
        # Interface 1
        "curated_context": None,
        # Interface 2
        "page_purpose": None,
        "historical_case": None,
        "narrative": None,
        "raw_narrative": None,
        # Interface 3
        "charts": None,
        "glossaries": None,
        "pages": None,
        "sources": None,
        "hallucination_checklist": None,
        "home_icon": None,
        # 출력
        "full_output": None,
        "output_path": None,
        # DB 저장
        "db_result": None,
        # 메타
        "error": None,
        "metrics": {},
    }


def _save_curated_topics(curated_topics: list) -> Path:
    """curated_topics를 output/curated_ALL_{date}.json으로 저장."""
    from .config import kst_today
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = kst_today().isoformat()
    path = OUTPUT_DIR / f"curated_ALL_{today}.json"
    payload = {"topics": curated_topics}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("curated_topics 저장: %s (%d topics)", path, len(curated_topics))
    return path


def _log_metrics(metrics: dict) -> None:
    """노드별 실행 시간 로그 출력."""
    if metrics:
        logger.info("--- 노드별 실행 시간 ---")
        for node_name, info in metrics.items():
            logger.info("  %s: %.2fs (%s)", node_name, info["elapsed_s"], info["status"])


def _log_llm_stats(stats: dict) -> None:
    totals = stats.get("totals", {}) if isinstance(stats, dict) else {}
    calls = int(totals.get("calls", 0) or 0)
    if calls <= 0:
        logger.info("--- LLM 사용량 요약 ---")
        logger.info("  호출 없음")
        return

    prompt_tokens = int(totals.get("prompt_tokens", 0) or 0)
    completion_tokens = int(totals.get("completion_tokens", 0) or 0)
    elapsed_s = float(totals.get("elapsed_s", 0.0) or 0.0)
    logger.info("--- LLM 사용량 요약 ---")
    logger.info(
        "  total calls=%d, prompt_tokens=%d, completion_tokens=%d, elapsed=%.2fs",
        calls,
        prompt_tokens,
        completion_tokens,
        elapsed_s,
    )

    by_prompt = stats.get("by_prompt", {}) if isinstance(stats, dict) else {}
    ranked = sorted(
        by_prompt.items(),
        key=lambda item: (
            int((item[1] or {}).get("prompt_tokens", 0))
            + int((item[1] or {}).get("completion_tokens", 0))
        ),
        reverse=True,
    )
    for prompt_name, bucket in ranked:
        events = bucket.get("events", {}) if isinstance(bucket, dict) else {}
        event_text = ", ".join(
            f"{k}={v}" for k, v in sorted(events.items()) if int(v or 0) > 0
        ) or "-"
        logger.info(
            "  prompt=%s calls=%d tokens=%d/%d elapsed=%.2fs events=%s",
            prompt_name,
            int(bucket.get("calls", 0) or 0),
            int(bucket.get("prompt_tokens", 0) or 0),
            int(bucket.get("completion_tokens", 0) or 0),
            float(bucket.get("elapsed_s", 0.0) or 0.0),
            event_text,
        )


def _log_crawl_status(final_state: dict) -> None:
    news_status = final_state.get("crawl_news_status")
    if isinstance(news_status, dict):
        logger.info(
            "crawl_news_status: requested=%s used=%s attempts=%s count=%s fallback=%s error=%s",
            news_status.get("requested_date"),
            news_status.get("used_date"),
            news_status.get("attempts"),
            news_status.get("count"),
            news_status.get("fallback_used"),
            news_status.get("error"),
        )

    research_status = final_state.get("crawl_research_status")
    if isinstance(research_status, dict):
        logger.info(
            "crawl_research_status: requested=%s used=%s attempts=%s count=%s fallback=%s error=%s",
            research_status.get("requested_date"),
            research_status.get("used_date"),
            research_status.get("attempts"),
            research_status.get("count"),
            research_status.get("fallback_used"),
            research_status.get("error"),
        )


async def async_main() -> int:
    # LangSmith 트레이싱을 위한 고유 실행 ID
    run_id = uuid4()
    os.environ.setdefault("LANGCHAIN_RUN_ID", str(run_id))
    logger.info("Pipeline run_id: %s", run_id)

    args = parse_args()
    backend = pick_backend(args.backend)

    # 파일 모드에서 경로 확인
    if args.input and not args.input.exists():
        logger.error("입력 파일을 찾을 수 없습니다: %s", args.input)
        return 1

    mode = "파일 로드" if args.input else "실시간 데이터 수집"

    logger.info("=== Datapipeline ===")
    logger.info("Mode: %s", mode)
    if args.input:
        logger.info("Input: %s", args.input)
    else:
        logger.info("Market: %s", args.market)
    logger.info("Backend: %s", backend)
    logger.info("Topic Count: %d", args.topic_count)

    # LangGraph 빌드
    from .graph import build_graph

    graph = build_graph()

    total_started = time.time()
    success_count = 0
    fail_count = 0

    # ── 파일 로드 모드: 단일 토픽 실행 (기존 동작 유지) ──
    if args.input:
        logger.info("Topic Index: %d", args.topic_index)
        reset_llm_stats()
        initial_state = _build_initial_state(
            input_path=str(args.input.resolve()),
            topic_index=args.topic_index,
            backend=backend,
            market=args.market,
        )

        started = time.time()
        final_state = await graph.ainvoke(initial_state)
        elapsed = time.time() - started

        if final_state.get("error"):
            logger.error("파이프라인 실패: %s", final_state["error"])
            return 1

        logger.info("=== 완료 ===")
        logger.info("출력 파일: %s", final_state.get("output_path", ""))
        logger.info("총 소요시간: %.2fs", elapsed)
        _log_crawl_status(final_state)
        _log_metrics(final_state.get("metrics", {}))
        _log_llm_stats(snapshot_llm_stats())
        return 0

    # ── 데이터 수집 모드: 멀티 토픽 루프 ──
    topic_count = args.topic_count
    curated_all_path: Path | None = None

    for idx in range(topic_count):
        logger.info("=== Topic %d/%d ===", idx + 1, topic_count)

        if idx == 0:
            # 1차: 전체 파이프라인 (데이터 수집 → Interface 2/3 → DB)
            reset_llm_stats()
            initial_state = _build_initial_state(
                input_path=None,
                topic_index=0,
                backend=backend,
                market=args.market,
            )

            started = time.time()
            final_state = await graph.ainvoke(initial_state)
            elapsed = time.time() - started

            if final_state.get("error"):
                logger.error("Topic 1/%d 실패: %s", topic_count, final_state["error"])
                fail_count += 1
                break  # 1차 실패 시 중단 (curated_topics 없음)

            logger.info("Topic 1/%d 완료: %s (%.2fs)", topic_count, final_state.get("output_path", ""), elapsed)
            _log_crawl_status(final_state)
            _log_metrics(final_state.get("metrics", {}))
            _log_llm_stats(snapshot_llm_stats())
            success_count += 1

            # curated_topics 저장 (2차+ 재활용)
            curated_topics = final_state.get("curated_topics")
            if curated_topics and len(curated_topics) > 1:
                curated_all_path = _save_curated_topics(curated_topics)
            else:
                logger.warning("curated_topics가 %d개뿐이므로 추가 토픽 생성을 건너뜁니다.", len(curated_topics or []))
                break
        else:
            # 2차+: curated_ALL 파일 로드 → Interface 2/3만 실행
            if not curated_all_path:
                logger.warning("curated_ALL 파일 없음, Topic %d/%d 건너뜀", idx + 1, topic_count)
                fail_count += 1
                continue

            initial_state = _build_initial_state(
                input_path=str(curated_all_path),
                topic_index=idx,
                backend=backend,
                market=args.market,
            )

            started = time.time()
            try:
                reset_llm_stats()
                final_state = await graph.ainvoke(initial_state)
                elapsed = time.time() - started

                if final_state.get("error"):
                    logger.error("Topic %d/%d 실패: %s", idx + 1, topic_count, final_state["error"])
                    fail_count += 1
                    continue  # 실패해도 다음 토픽 진행

                logger.info("Topic %d/%d 완료: %s (%.2fs)", idx + 1, topic_count, final_state.get("output_path", ""), elapsed)
                _log_crawl_status(final_state)
                _log_metrics(final_state.get("metrics", {}))
                _log_llm_stats(snapshot_llm_stats())
                success_count += 1
            except Exception as e:
                elapsed = time.time() - started
                logger.error("Topic %d/%d 예외: %s (%.2fs)", idx + 1, topic_count, e, elapsed)
                fail_count += 1
                continue

    total_elapsed = time.time() - total_started
    logger.info("=== 전체 완료 ===")
    logger.info("성공: %d, 실패: %d, 총 소요시간: %.2fs", success_count, fail_count, total_elapsed)

    return 0 if success_count > 0 else 1


def main() -> int:
    import asyncio
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
