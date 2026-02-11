#!/usr/bin/env python3
"""키워드 품질 자동 검증 스크립트.

생성된 키워드의 품질을 자동으로 측정하고 리포트를 출력합니다.
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
script_path = Path(__file__).resolve()
if script_path.parts[-2] == "scripts":  # Docker: /app/scripts/verify_keywords.py
    app_root = script_path.parent.parent  # /app
else:  # Local: /project/scripts/verify_keywords.py
    app_root = script_path.parents[2] / "fastapi"
sys.path.insert(0, str(app_root))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.briefing import DailyBriefing, BriefingStock


async def verify_keywords():
    """최근 브리핑의 키워드 품질 검증."""
    async with AsyncSessionLocal() as session:
        # 최근 브리핑 조회
        result = await session.execute(
            select(DailyBriefing).order_by(DailyBriefing.created_at.desc()).limit(1)
        )
        briefing = result.scalar_one_or_none()

        if not briefing:
            print("❌ 브리핑 없음")
            return

        keywords = briefing.top_keywords.get("keywords", [])
        print(f"\n📊 키워드 품질 리포트 ({briefing.briefing_date})")
        print("=" * 60)

        if not keywords:
            print("❌ 키워드 없음")
            return

        # 관련 종목 정보 조회
        stock_result = await session.execute(
            select(BriefingStock)
            .where(BriefingStock.briefing_id == briefing.id)
        )
        stocks = stock_result.scalars().all()

        print(f"\n📈 종목 정보: {len(stocks)}개")
        for stock in stocks[:5]:  # 상위 5개만 표시
            trend_info = f"{stock.trend_type} ({stock.trend_days}일)" if stock.trend_type else "N/A"
            catalyst_info = f"✓" if stock.catalyst else "✗"
            print(f"  - {stock.stock_name} ({stock.stock_code}): {trend_info}, 카탈리스트: {catalyst_info}")
        if len(stocks) > 5:
            print(f"  ... 외 {len(stocks) - 5}개")

        # 키워드 품질 메트릭 계산
        metrics = {
            "total_keywords": len(keywords),
            "has_sector": 0,
            "has_catalyst": 0,
            "has_sources": 0,
            "multi_stock": 0,
            "has_mirroring_hint": 0,
            "trend_days_avg": 0,
            "template_phrases": 0,
            "quality_score_avg": 0,
        }

        print(f"\n🔑 키워드 분석:")
        for i, kw in enumerate(keywords, 1):
            print(f"\n키워드 #{i}: {kw.get('title', 'N/A')}")

            # 섹터
            if kw.get("sector"):
                metrics["has_sector"] += 1
                print(f"  ✓ 섹터: {kw['sector']}")
            else:
                print(f"  ✗ 섹터 없음")

            # 카탈리스트
            if kw.get("catalyst"):
                metrics["has_catalyst"] += 1
                print(f"  ✓ 카탈리스트: {kw['catalyst'][:50]}...")
            else:
                print(f"  ✗ 카탈리스트 없음")

            # 출처 정보
            if kw.get("sources"):
                metrics["has_sources"] += 1
                sources = kw["sources"]
                print(f"  ✓ 출처 정보:")
                if sources.get("market_data"):
                    print(f"    - 시장 데이터: {sources['market_data'].get('provider', 'N/A')}")
                if sources.get("news"):
                    print(f"    - 뉴스: {len(sources['news'])}건")
                if sources.get("sector_info"):
                    print(f"    - 섹터 정보: {sources['sector_info'].get('provider', 'N/A')}")
            else:
                print(f"  ✗ 출처 정보 없음")

            # 다종목 그룹화
            stock_count = len(kw.get("stocks", []))
            if stock_count >= 2:
                metrics["multi_stock"] += 1
                print(f"  ✓ 다종목 그룹화: {stock_count}개")
            else:
                print(f"  ✗ 개별 종목: {stock_count}개")

            # 과거 사례 힌트
            if kw.get("mirroring_hint"):
                metrics["has_mirroring_hint"] += 1
                print(f"  ✓ 과거 사례: {kw['mirroring_hint'][:50]}...")
            else:
                print(f"  ✗ 과거 사례 없음")

            # 트렌드 일수
            trend_days = kw.get("trend_days", 0)
            metrics["trend_days_avg"] += trend_days
            if trend_days > 0:
                print(f"  ✓ 트렌드: {trend_days}일 연속")
            else:
                print(f"  ✗ 트렌드 정보 없음")

            # 품질 점수
            quality_score = kw.get("quality_score", 0)
            metrics["quality_score_avg"] += quality_score
            print(f"  📊 품질 점수: {quality_score}/100")

            # 템플릿 문구 감지
            title = kw.get("title", "")
            template_phrases = ["지속될까", "반전 신호", "주목", "확대될까"]
            if any(p in title for p in template_phrases):
                metrics["template_phrases"] += 1
                print(f"  ⚠️  템플릿 문구 사용")

        # 평균 계산
        if metrics["total_keywords"] > 0:
            metrics["trend_days_avg"] /= metrics["total_keywords"]
            metrics["quality_score_avg"] /= metrics["total_keywords"]

        # 종합 리포트
        print(f"\n" + "=" * 60)
        print(f"📋 종합 리포트")
        print(f"=" * 60)
        print(f"전체 키워드 수: {metrics['total_keywords']}")
        print(f"섹터 정보 포함: {metrics['has_sector']}/{metrics['total_keywords']}")
        print(f"카탈리스트 연결: {metrics['has_catalyst']}/{metrics['total_keywords']}")
        print(f"출처 정보 포함: {metrics['has_sources']}/{metrics['total_keywords']}")
        print(f"다종목 그룹화: {metrics['multi_stock']}/{metrics['total_keywords']}")
        print(f"과거 사례 힌트: {metrics['has_mirroring_hint']}/{metrics['total_keywords']}")
        print(f"평균 트렌드 일수: {metrics['trend_days_avg']:.1f}일")
        print(f"평균 품질 점수: {metrics['quality_score_avg']:.1f}/100")
        print(f"⚠️  템플릿 문구 사용: {metrics['template_phrases']}/{metrics['total_keywords']}")

        # 전체 품질 점수 (0-100)
        overall_score = 0
        total = metrics["total_keywords"]

        # 각 메트릭별 가중치
        overall_score += (metrics["has_sector"] / total) * 15
        overall_score += (metrics["has_catalyst"] / total) * 20
        overall_score += (metrics["has_sources"] / total) * 10
        overall_score += (metrics["multi_stock"] / total) * 15
        overall_score += (metrics["has_mirroring_hint"] / total) * 15
        overall_score += min(20, metrics["trend_days_avg"] * 5)
        overall_score += max(0, 5 - metrics["template_phrases"] * 2)  # 페널티

        print(f"\n🎯 전체 품질 점수: {overall_score:.0f}/100")
        if overall_score >= 80:
            print("✅ 우수 - 키워드 품질이 매우 좋습니다")
        elif overall_score >= 60:
            print("⚠️  보통 - 개선이 필요합니다")
        else:
            print("❌ 불량 - 파이프라인 점검이 필요합니다")

        # 개선 제안
        print(f"\n💡 개선 제안:")
        if metrics["has_catalyst"] < total:
            print(f"  - RSS 뉴스 매칭 강화 필요 ({total - metrics['has_catalyst']}개 키워드에 카탈리스트 없음)")
        if metrics["multi_stock"] < total * 0.5:
            print(f"  - 섹터 클러스터링 강화 필요 (개별 종목 비율이 높음)")
        if metrics["has_mirroring_hint"] < total:
            print(f"  - 과거 사례 힌트 추가 필요 ({total - metrics['has_mirroring_hint']}개 키워드에 힌트 없음)")
        if metrics["template_phrases"] > 0:
            print(f"  - LLM 프롬프트 개선 필요 (템플릿 문구 제거)")
        if metrics["trend_days_avg"] < 2:
            print(f"  - 트렌드 필터링 기준 강화 필요 (평균 트렌드 일수가 낮음)")


if __name__ == "__main__":
    asyncio.run(verify_keywords())
