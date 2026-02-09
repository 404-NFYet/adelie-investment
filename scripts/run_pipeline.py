#!/usr/bin/env python3
"""내러티브 파이프라인 실행 스크립트.

사용법:
    python3 scripts/run_pipeline.py              # 실제 AI 호출 + DB 저장
    python3 scripts/run_pipeline.py --dry-run     # 더미 데이터로 테스트
    python3 scripts/run_pipeline.py --count 5     # 시나리오 5개 생성
    python3 scripts/run_pipeline.py --no-save     # AI 생성만, DB 저장 생략
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def setup_logging(verbose: bool = False):
    """로깅 설정."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # httpx 로그 억제
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_db_url() -> str:
    """DATABASE_URL 환경변수에서 DB URL 가져오기."""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL이 .env에 설정되지 않았습니다.")
    return db_url


def main():
    parser = argparse.ArgumentParser(description="내러티브 파이프라인 실행")
    parser.add_argument("--dry-run", action="store_true", help="더미 데이터로 테스트 (API 호출 없음)")
    parser.add_argument("--count", type=int, default=3, help="생성할 시나리오 수 (기본: 3)")
    parser.add_argument("--no-save", action="store_true", help="DB 저장 생략")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그")
    parser.add_argument("--output", "-o", type=str, help="결과 JSON을 파일로 저장")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("pipeline")

    logger.info("=" * 60)
    logger.info("  내러티브 파이프라인 시작")
    logger.info("  dry_run=%s, count=%d, save=%s", args.dry_run, args.count, not args.no_save)
    logger.info("=" * 60)

    # AI 서비스 초기화
    from ai_module.services.multi_provider_client import MultiProviderClient
    from ai_module.pipeline import BriefingGenerator, PipelineAIService

    client = MultiProviderClient()
    ai_service = PipelineAIService(client=client, dry_run=args.dry_run)

    # 파이프라인 실행
    generator = BriefingGenerator(
        ai_service=ai_service,
        target_scenario_count=args.count,
        dry_run=args.dry_run,
    )

    briefing_data = generator.run()

    # 결과 요약
    scenarios = briefing_data.get("scenarios", [])
    logger.info("")
    logger.info("=" * 60)
    logger.info("  생성 결과 요약")
    logger.info("=" * 60)
    for i, s in enumerate(scenarios, 1):
        logger.info("  [%d] %s", i, s.get("keyword", ""))
        logger.info("      제목: %s", s.get("title", ""))
        logger.info("      유사도: %s%%", s.get("similarity_score", "?"))
        narrative = s.get("narrative", {})
        step_keys = list(narrative.keys()) if isinstance(narrative, dict) else []
        logger.info("      내러티브 스텝: %s", step_keys)

    # JSON 파일 저장 (선택)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(briefing_data, f, ensure_ascii=False, indent=2, default=str)
        logger.info("결과 JSON 저장: %s", output_path)

    # DB 저장
    if not args.no_save:
        db_url = get_db_url()
        logger.info("DB 저장 시작: %s", db_url.split("@")[-1] if "@" in db_url else "***")

        save_result = generator.save_to_db(briefing_data, db_url)
        logger.info("DB 저장 완료: %s", save_result)
    else:
        logger.info("--no-save 옵션: DB 저장 생략")

    logger.info("")
    logger.info("파이프라인 완료!")


if __name__ == "__main__":
    main()
