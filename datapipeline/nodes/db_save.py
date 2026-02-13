"""LangGraph 노드: 파이프라인 결과를 DB에 저장한다."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def save_to_db_node(state: dict[str, Any]) -> dict[str, Any]:
    """assemble_output 이후 실행되는 DB 저장 노드.

    full_output이 없거나 에러 상태면 건너뛴다.
    DATABASE_URL 미설정 또는 DB 연결 실패 시에도 정상 종료 (skip).
    """
    started = time.time()

    full_output = state.get("full_output")
    if not full_output:
        logger.warning("full_output이 없어 DB 저장을 건너뜁니다.")
        return {
            "metrics": {
                "save_to_db": {"elapsed_s": time.time() - started, "status": "skipped"},
            },
        }

    from datapipeline.db.writer import save_briefing_to_db

    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = loop.run_in_executor(
                    pool, lambda: asyncio.run(save_briefing_to_db(full_output))
                )
                # LangGraph 노드는 동기 함수이므로 이 경로는 보통 안 탐
                result = asyncio.run(save_briefing_to_db(full_output))
        except RuntimeError:
            result = asyncio.run(save_briefing_to_db(full_output))
    except Exception as e:
        elapsed = time.time() - started
        logger.warning("DB 저장 실패 (파이프라인은 정상 완료): %s", e)
        return {
            "db_result": {"skipped": True, "reason": str(e)},
            "metrics": {
                "save_to_db": {"elapsed_s": elapsed, "status": "error"},
            },
        }

    elapsed = time.time() - started

    if result.get("skipped"):
        logger.info("DB 저장 건너뜀: %s", result.get("reason", "DATABASE_URL 미설정"))
        status = "skipped"
    else:
        logger.info("DB 저장 완료: %s (%.2fs)", result, elapsed)
        status = "success"

    return {
        "db_result": result,
        "metrics": {
            "save_to_db": {"elapsed_s": elapsed, "status": status},
        },
    }
