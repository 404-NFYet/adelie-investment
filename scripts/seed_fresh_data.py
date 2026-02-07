"""새 데이터 생성 스크립트 - deploy-test에서 실행."""
import asyncio
import json
import os
from datetime import datetime, timedelta
from pykrx import stock

def collect_and_seed():
    today = datetime.now()
    if today.weekday() >= 5:
        today -= timedelta(days=(today.weekday() - 4))
    date_str = today.strftime("%Y%m%d")
    print(f"수집 날짜: {date_str}")

    df = stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
    df = df[df["거래량"] > 0]
    print(f"전체 종목: {len(df)}")

    df_sorted = df.sort_values("등락률", ascending=False)

    def extract_stocks(tickers):
        result = []
        for t in tickers:
            name = stock.get_market_ticker_name(t)
            row = df.loc[t] if t in df.index else df_sorted.loc[t]
            result.append({
                "stock_code": t, "stock_name": name,
                "close": int(row["종가"]), "change_rate": round(float(row["등락률"]), 2),
                "volume": int(row["거래량"])
            })
        return result

    gainers = extract_stocks(df_sorted.head(5).index)
    losers = extract_stocks(df_sorted.tail(5).index)
    high_vol = extract_stocks(df.sort_values("거래량", ascending=False).head(5).index)

    try:
        kospi = stock.get_index_ohlcv(date_str, date_str, "1001")
        kosdaq = stock.get_index_ohlcv(date_str, date_str, "2001")
        market_summary = f"KOSPI {kospi.iloc[0]['종가']:.2f}, KOSDAQ {kosdaq.iloc[0]['종가']:.2f}"
    except Exception:
        market_summary = "시장 지수 조회 중"

    print(f"시장: {market_summary}")

    keywords = [
        {"title": f"{gainers[0]['stock_name']}, 급등세 지속될까?",
         "category": "급등주", "description": f"{gainers[0]['change_rate']:+.1f}% 급등",
         "stocks": [
             {"stock_code": g["stock_code"], "stock_name": g["stock_name"],
              "reason": f"등락률 {g['change_rate']:+.1f}%, 오늘 급등주 상위"}
             for g in gainers[:2]
         ],
         "tagline": "급등주 분석"},
        {"title": f"변동성 확대, {losers[0]['stock_name']} 주의보",
         "category": "급락주", "description": f"{losers[0]['change_rate']:.1f}% 하락",
         "stocks": [
             {"stock_code": l["stock_code"], "stock_name": l["stock_name"],
              "reason": f"등락률 {l['change_rate']:.1f}%, 오늘 급락 종목"}
             for l in losers[:2]
         ],
         "tagline": "급락 종목"},
        {"title": "거래량 폭발! 거래량이 말하는 것",
         "category": "거래량", "description": f"{high_vol[0]['stock_name']} 주목",
         "stocks": [
             {"stock_code": h["stock_code"], "stock_name": h["stock_name"],
              "reason": f"거래량 {h['volume']:,}주, 거래량 상위 종목"}
             for h in high_vol[:2]
         ],
         "tagline": "거래량 분석"},
        {"title": "모멘텀 투자, 수익률의 비밀",
         "category": "투자전략", "description": "추세 추종 전략 분석",
         "stocks": [
             {"stock_code": gainers[2]["stock_code"], "stock_name": gainers[2]["stock_name"],
              "reason": f"등락률 {gainers[2]['change_rate']:+.1f}%, 모멘텀 상승 신호"},
             {"stock_code": gainers[3]["stock_code"], "stock_name": gainers[3]["stock_name"],
              "reason": f"등락률 {gainers[3]['change_rate']:+.1f}%, 추세 추종 대상"},
         ],
         "tagline": "모멘텀 전략"},
        {"title": "PER로 보는 저평가 종목 찾기",
         "category": "가치투자", "description": "밸류에이션 분석",
         "stocks": [
             {"stock_code": high_vol[2]["stock_code"], "stock_name": high_vol[2]["stock_name"],
              "reason": f"거래량 {high_vol[2]['volume']:,}주, 가치투자 관심 종목"},
             {"stock_code": high_vol[3]["stock_code"], "stock_name": high_vol[3]["stock_name"],
              "reason": f"거래량 {high_vol[3]['volume']:,}주, 밸류에이션 분석 대상"},
         ],
         "tagline": "가치투자"},
    ]

    top_keywords = {"keywords": keywords}
    print(f"키워드 {len(keywords)}개 (동적 용어 포함: 변동성, 거래량, 모멘텀, PER)")

    async def insert():
        import asyncpg
        db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
        if not db_url:
            db_url = "postgresql://narative:password@postgres:5432/narrative_invest"
        conn = await asyncpg.connect(db_url)

        bid = await conn.fetchval(
            "INSERT INTO daily_briefings (briefing_date, market_summary, top_keywords, created_at) VALUES ($1, $2, $3::jsonb, NOW()) RETURNING id",
            today.date(), market_summary, json.dumps(top_keywords, ensure_ascii=False))
        print(f"daily_briefings: id={bid}")

        rows = []
        for cat, stks in [("gainer", gainers), ("loser", losers), ("high_volume", high_vol)]:
            for s in stks:
                rows.append((bid, s["stock_code"], s["stock_name"], s["change_rate"], s["volume"], cat, datetime.now()))
        await conn.executemany(
            "INSERT INTO briefing_stocks (briefing_id, stock_code, stock_name, change_rate, volume, selection_reason, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7)", rows)
        print(f"briefing_stocks: {len(rows)}건")
        await conn.close()

    asyncio.run(insert())
    print("=== 완료 ===")

if __name__ == "__main__":
    collect_and_seed()
