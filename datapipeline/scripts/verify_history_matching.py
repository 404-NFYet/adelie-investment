#!/usr/bin/env python3
"""히스토리 매칭 품질 검증 스크립트.

generate_cases.py로 생성된 히스토리 케이스의 매칭 품질을 검증합니다.
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
script_path = Path(__file__).resolve()
if script_path.parts[-2] == "scripts":  # Docker: /app/scripts/verify_history_matching.py
    app_root = script_path.parent.parent  # /app
else:  # Local: /project/scripts/verify_history_matching.py
    app_root = script_path.parents[2] / "fastapi"
sys.path.insert(0, str(app_root))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.historical_case import HistoricalCase


async def verify_history_matching():
    """히스토리 매칭 품질 검증."""
    async with AsyncSessionLocal() as session:
        # 최근 케이스 조회 (최대 10개)
        result = await session.execute(
            select(HistoricalCase)
            .order_by(HistoricalCase.created_at.desc())
            .limit(10)
        )
        cases = result.scalars().all()

        if not cases:
            print("❌ 히스토리 케이스 없음")
            print("\n💡 힌트: generate_cases.py를 먼저 실행하세요:")
            print("   docker exec adelie-backend-api python /app/generate_cases.py")
            return

        # 전체 케이스 수 조회
        total_count = await session.scalar(select(func.count()).select_from(HistoricalCase))

        print(f"\n🔍 히스토리 매칭 품질 검증")
        print("=" * 60)
        print(f"전체 케이스 수: {total_count}개")
        print(f"검증 대상: 최근 {len(cases)}개\n")

        metrics = {
            "total": len(cases),
            "has_keyword": 0,
            "has_story": 0,
            "has_comparison": 0,
            "has_past_company": 0,
            "has_past_year": 0,
            "abstract_matching": 0,  # 추상적 매칭 (거시 주제)
            "specific_matching": 0,  # 구체적 매칭 (종목+연도)
            "past_years": [],  # 과거 사례 연도 분포
        }

        for i, case in enumerate(cases, 1):
            keyword = case.keyword or "N/A"
            story = case.story or ""
            comp_data = case.comparison_data or {}

            print(f"케이스 #{i}: {case.id}")
            print(f"  키워드: {keyword}")

            # 키워드 존재 여부
            if case.keyword:
                metrics["has_keyword"] += 1
                print(f"  ✓ 키워드 존재")
            else:
                print(f"  ✗ 키워드 없음")

            # 스토리 존재 여부
            if story and len(story) > 50:
                metrics["has_story"] += 1
                print(f"  ✓ 스토리 생성 ({len(story)}자)")
            else:
                print(f"  ✗ 스토리 부족 ({len(story)}자)")

            # 비교 데이터 존재 여부
            if comp_data:
                metrics["has_comparison"] += 1
                print(f"  ✓ 비교 데이터 존재")

                # 과거 케이스 정보 추출
                past_metric = comp_data.get("past_metric", {})
                past_company = past_metric.get("company", "N/A")
                past_year = past_metric.get("year", "N/A")

                if past_company and past_company != "N/A":
                    metrics["has_past_company"] += 1

                if past_year and past_year != "N/A":
                    metrics["has_past_year"] += 1
                    if isinstance(past_year, (int, str)) and str(past_year).isdigit():
                        metrics["past_years"].append(int(past_year))

                print(f"    - 과거 케이스: {past_company} ({past_year})")

                # 구체성 체크
                abstract_keywords = ["금융", "시장", "경제", "전반", "업종", "산업", "국내", "글로벌"]
                if any(word in str(past_company) for word in abstract_keywords):
                    metrics["abstract_matching"] += 1
                    print(f"    ⚠️  추상적 매칭 (거시 주제)")
                elif past_company != "N/A" and past_year != "N/A":
                    metrics["specific_matching"] += 1
                    print(f"    ✅ 구체적 매칭 (종목+연도)")
                else:
                    print(f"    ⚠️  정보 부족")
            else:
                print(f"  ✗ 비교 데이터 없음")

            print()

        # 종합 리포트
        print("=" * 60)
        print("📋 종합 리포트")
        print("=" * 60)
        print(f"키워드 존재: {metrics['has_keyword']}/{metrics['total']}")
        print(f"스토리 생성: {metrics['has_story']}/{metrics['total']}")
        print(f"비교 데이터: {metrics['has_comparison']}/{metrics['total']}")
        print(f"과거 기업명: {metrics['has_past_company']}/{metrics['total']}")
        print(f"과거 연도: {metrics['has_past_year']}/{metrics['total']}")
        print(f"구체적 매칭: {metrics['specific_matching']}/{metrics['total']}")
        print(f"추상적 매칭: {metrics['abstract_matching']}/{metrics['total']}")

        # 과거 사례 연도 분포
        if metrics["past_years"]:
            year_min = min(metrics["past_years"])
            year_max = max(metrics["past_years"])
            year_avg = sum(metrics["past_years"]) / len(metrics["past_years"])
            print(f"\n📅 과거 사례 연도 분포:")
            print(f"  최소: {year_min}년")
            print(f"  최대: {year_max}년")
            print(f"  평균: {year_avg:.1f}년")

        # 품질 점수 (0-100)
        score = 0
        total = metrics["total"]

        if total > 0:
            score += (metrics["has_keyword"] / total) * 20
            score += (metrics["has_story"] / total) * 20
            score += (metrics["has_comparison"] / total) * 20
            score += (metrics["has_past_company"] / total) * 15
            score += (metrics["has_past_year"] / total) * 15
            score += (metrics["specific_matching"] / total) * 10
            # 추상적 매칭은 감점
            if metrics["abstract_matching"] > 0:
                score -= (metrics["abstract_matching"] / total) * 10

        print(f"\n🎯 전체 품질 점수: {score:.0f}/100")
        if score >= 80:
            print("✅ 우수 - 히스토리 매칭이 매우 좋습니다")
        elif score >= 60:
            print("⚠️  보통 - 개선이 필요합니다")
        else:
            print("❌ 불량 - generate_cases.py 점검이 필요합니다")

        # 개선 제안
        print(f"\n💡 개선 제안:")
        if metrics["has_story"] < total:
            print(f"  - 스토리 생성 강화 필요 ({total - metrics['has_story']}개 케이스에 스토리 부족)")
        if metrics["specific_matching"] < total * 0.7:
            print(f"  - 구체적 매칭 강화 필요 (종목명+연도 포함 비율 낮음)")
        if metrics["abstract_matching"] > total * 0.3:
            print(f"  - 추상적 매칭 감소 필요 (거시 주제 비율이 높음)")
        if metrics["past_years"] and min(metrics["past_years"]) > 2015:
            print(f"  - 더 오래된 사례 발굴 필요 (최소 {min(metrics['past_years'])}년)")


if __name__ == "__main__":
    asyncio.run(verify_history_matching())
