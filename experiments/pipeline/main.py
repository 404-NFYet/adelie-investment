"""파이프라인 메인 - 실험용 실행 모듈.

CLI 또는 다른 스크립트에서 호출하여 파이프라인을 실행한다.
"""

from __future__ import annotations

import logging
from datetime import date

from pipeline.config import PipelineConfig
from pipeline.generator import PipelineGenerator

LOGGER = logging.getLogger(__name__)


async def run_pipeline(
    config: PipelineConfig | None = None,
    target_date: date | None = None,
    save_json: bool = True,
    save_db: bool = False,
) -> dict:
    """파이프라인 실행 메인 함수.

    Args:
        config: 파이프라인 설정 (None이면 기본값 사용)
        target_date: 대상 날짜 (None이면 오늘 KST)
        save_json: 결과를 JSON 파일로 저장
        save_db: 결과를 DB에 저장

    Returns:
        실행 결과 요약 딕셔너리
    """
    cfg = config or PipelineConfig()

    LOGGER.info("파이프라인 설정:")
    LOGGER.info("  시나리오 개수: %d", cfg.target_scenario_count)
    LOGGER.info("  키워드 모델: %s", cfg.keyword_model)
    LOGGER.info("  리서치 모델: %s", cfg.research_model)
    LOGGER.info("  스토리 모델: %s", cfg.story_model)

    generator = PipelineGenerator(config=cfg)
    result = await generator.generate(target_date=target_date, save_json=save_json)

    # DB 저장 (선택)
    if save_db and result.scenarios:
        try:
            from pipeline.repository import PipelineRepository

            repo = PipelineRepository(cfg)
            import dataclasses

            scenarios_data = [dataclasses.asdict(s) for s in result.scenarios]
            narrative_id = await repo.save_pipeline_result(
                target_date=date.fromisoformat(result.date),
                keywords=[s.keyword for s in result.scenarios],
                scenarios=scenarios_data,
                glossary=result.glossary,
            )
            LOGGER.info("DB 저장 완료: %s", narrative_id)
            await repo.close()
        except Exception as exc:
            LOGGER.warning("DB 저장 실패 (무시): %s", exc)

    # 결과 요약
    summary = {
        "date": result.date,
        "scenarios_count": len(result.scenarios),
        "keywords": [s.keyword for s in result.scenarios],
        "elapsed_seconds": result.elapsed_seconds,
        "errors": result.errors,
        "glossary_terms": list(result.glossary.keys()),
    }

    LOGGER.info("결과 요약: %s", summary)
    return summary
