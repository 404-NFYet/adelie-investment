#!/usr/bin/env python3
"""Adelie Experiments - 파이프라인 실행 엔트리 포인트.

Usage:
    python run.py                  # 전체 파이프라인 실행
    python run.py --step keywords  # 키워드 추출만
    python run.py --step research  # 리서치만
    python run.py --step story     # 스토리 생성만
    python run.py --collect rss    # RSS 수집만
    python run.py --collect naver  # 네이버 리포트 수집만
"""

import argparse
import asyncio
import logging
import sys

from pipeline.config import PipelineConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger("experiments")


async def run_full_pipeline(config: PipelineConfig) -> None:
    """전체 파이프라인 실행."""
    from pipeline.main import run_pipeline

    await run_pipeline(config)


async def run_step(config: PipelineConfig, step: str) -> None:
    """개별 단계 실행."""
    if step == "keywords":
        from pipeline.rss_service import RSSService
        from pipeline.ai_service import AIPipelineService

        rss = RSSService()
        ai = AIPipelineService(config)
        news = await rss.fetch_top_news()
        keywords = await ai.extract_top_keywords(news)
        LOGGER.info("추출된 키워드: %s", [k.keyword for k in keywords])

    elif step == "research":
        from pipeline.ai_service import AIPipelineService

        ai = AIPipelineService(config)
        keyword = input("리서치할 키워드 입력: ").strip()
        ctx, citations = await ai.research_context(keyword)
        LOGGER.info("리서치 결과 (%d자, 인용 %d개)", len(ctx), len(citations))
        print(ctx[:500])

    elif step == "story":
        from pipeline.ai_service import AIPipelineService

        ai = AIPipelineService(config)
        keyword = input("스토리 생성 키워드: ").strip()
        ctx, _ = await ai.research_context(keyword)
        sim, _ = await ai.research_simulation(keyword)
        story = await ai.generate_story(keyword, ctx, sim)
        LOGGER.info("스토리 생성 완료: %d 섹션", len(story))

    else:
        LOGGER.error("알 수 없는 단계: %s (keywords, research, story 중 선택)", step)


async def run_collector(config: PipelineConfig, collector: str) -> None:
    """데이터 수집 실행."""
    if collector == "rss":
        from pipeline.rss_service import RSSService

        rss = RSSService()
        news = await rss.fetch_top_news()
        LOGGER.info("RSS 수집 완료: %d자", len(news))
        print(news[:1000])

    elif collector == "naver":
        from collectors.naver_industry import NaverIndustryCrawler
        from collectors.naver_economy import NaverEconomyCrawler
        from datetime import date

        today = date.today().strftime("%Y%m%d")
        LOGGER.info("네이버 리포트 수집: %s", today)

        industry = NaverIndustryCrawler()
        reports = await industry.fetch_reports(today)
        LOGGER.info("산업 리포트: %d건", len(reports))
        await industry.close()

        economy = NaverEconomyCrawler()
        eco_reports = await economy.fetch_reports(today)
        LOGGER.info("경제 리포트: %d건", len(eco_reports))
        await economy.close()

    else:
        LOGGER.error("알 수 없는 수집기: %s (rss, naver 중 선택)", collector)


def main() -> None:
    """CLI 엔트리 포인트."""
    parser = argparse.ArgumentParser(description="Adelie 파이프라인 실험")
    parser.add_argument("--step", type=str, help="개별 단계 실행 (keywords, research, story)")
    parser.add_argument("--collect", type=str, help="데이터 수집 (rss, naver)")
    args = parser.parse_args()

    config = PipelineConfig()
    if not config.validate():
        LOGGER.error("설정 검증 실패. .env 파일을 확인하세요.")
        sys.exit(1)

    if args.step:
        asyncio.run(run_step(config, args.step))
    elif args.collect:
        asyncio.run(run_collector(config, args.collect))
    else:
        asyncio.run(run_full_pipeline(config))


if __name__ == "__main__":
    main()
