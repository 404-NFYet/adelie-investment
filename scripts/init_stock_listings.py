"""stock_listings 테이블 초기 데이터 수집.

pykrx로 코스피/코스닥 전체 종목 수집 후
pykrx의 업종 분류 정보를 추가하여 DB에 저장.

최초 1회 실행 + 월 1회 cron으로 업데이트 권장.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from pykrx import stock as pykrx_stock
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.stock_listing import StockListing


async def init_stock_listings():
    """종목 목록 초기화."""
    today = datetime.now().strftime("%Y%m%d")
    listings = []

    print(f"📊 종목 목록 수집 시작 ({today})")
    print("=" * 60)

    # 1. pykrx로 코스피/코스닥 전체 종목 수집
    for market in ["KOSPI", "KOSDAQ"]:
        print(f"\n{market} 종목 수집 중...")
        try:
            tickers = pykrx_stock.get_market_ticker_list(today, market=market)
            print(f"  → {len(tickers)}개 종목 발견")

            for ticker in tickers:
                try:
                    name = pykrx_stock.get_market_ticker_name(ticker)
                    if name:
                        listings.append({
                            "stock_code": ticker,
                            "stock_name": name,
                            "market": market,
                            "sector": None,
                            "industry": None,
                        })
                except Exception as e:
                    print(f"  ⚠️  {ticker} 이름 조회 실패: {e}")
                    continue

        except Exception as e:
            print(f"❌ {market} 수집 실패: {e}")
            continue

    print(f"\n총 {len(listings)}개 종목 수집 완료")

    # 2. pykrx로 업종 정보 수집
    print("\n📈 pykrx로 업종 정보 수집 중...")
    sector_map = {}  # stock_code → sector(업종명)

    for market in ["KOSPI", "KOSDAQ"]:
        try:
            sector_df = pykrx_stock.get_market_sector_classifications(today, market=market)
            if sector_df is not None and not sector_df.empty:
                # DataFrame의 인덱스가 종목코드, '업종명' 컬럼이 섹터 정보
                for stock_code in sector_df.index:
                    sector_name = sector_df.loc[stock_code, "업종명"]
                    if sector_name and sector_name.strip():
                        sector_map[stock_code] = sector_name.strip()
                print(f"  → {market}: {len(sector_df)}개 종목 업종 정보 수집")
        except Exception as e:
            print(f"  ⚠️  {market} 업종 정보 수집 실패: {e}")
            continue

    # 3. 업종 정보를 listings에 매핑
    enriched_count = 0
    for item in listings:
        code = item["stock_code"]
        if code in sector_map:
            item["sector"] = sector_map[code]
            item["industry"] = sector_map[code]  # pykrx는 업종명만 제공하므로 동일하게 설정
            enriched_count += 1

    print(f"  → 총 {enriched_count}개 종목에 업종 정보 매핑 완료")
    if enriched_count < len(listings):
        print(f"  ⚠️  {len(listings) - enriched_count}개 종목은 업종 정보 없음")

    # 4. DB 저장
    print("\n💾 DB 저장 중...")
    async with AsyncSessionLocal() as session:
        # 기존 데이터 확인
        result = await session.execute(select(StockListing))
        existing = {row.stock_code for row in result.scalars().all()}

        new_count = 0
        update_count = 0

        for item in listings:
            code = item["stock_code"]

            if code in existing:
                # 업데이트
                await session.execute(
                    select(StockListing).filter(StockListing.stock_code == code)
                )
                listing = await session.scalar(
                    select(StockListing).filter(StockListing.stock_code == code)
                )
                if listing:
                    listing.stock_name = item["stock_name"]
                    listing.market = item["market"]
                    listing.sector = item.get("sector")
                    listing.industry = item.get("industry")
                    listing.is_active = True
                    listing.updated_at = datetime.utcnow()
                    update_count += 1
            else:
                # 신규 추가
                listing = StockListing(**item)
                session.add(listing)
                new_count += 1

        try:
            await session.commit()
            print(f"✅ 저장 완료: 신규 {new_count}개, 업데이트 {update_count}개")
        except IntegrityError as e:
            await session.rollback()
            print(f"❌ DB 저장 실패: {e}")
            raise

    print("\n" + "=" * 60)
    print(f"🎉 완료! 총 {len(listings)}개 종목 처리")


if __name__ == "__main__":
    print("🚀 stock_listings 테이블 초기화\n")
    asyncio.run(init_stock_listings())
