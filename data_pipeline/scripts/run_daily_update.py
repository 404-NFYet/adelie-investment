#!/usr/bin/env python3
"""Step 3: Daily update pipeline."""
import argparse, asyncio, os, sys, time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")
from sqlalchemy import create_engine, text

def get_engine():
    return create_engine(os.getenv("DATABASE_URL", "").replace("+asyncpg", ""))

def has_briefing(engine, d):
    with engine.connect() as c:
        r = c.execute(text("SELECT COUNT(*) FROM briefing_stocks bs JOIN daily_briefings db ON bs.briefing_id=db.id WHERE db.briefing_date=:d"), {"d": d}).fetchone()
    return r[0] > 0

async def run(date_str):
    t0 = time.time()
    print("=" * 60)
    print(f" Daily Update: {date_str}")
    print("=" * 60)
    engine = get_engine()
    print("\n[1/3] Stock data check")
    if has_briefing(engine, date_str):
        print("  Already exists. Skip.")
    else:
        print("  No stock data. Run stock collection first.")
        return
    print("\n[2/3] Keyword generation")
    from scripts.generate_keywords import main as gen_kw
    keywords = gen_kw(date_str)
    if not keywords:
        print("  FAILED"); return
    print("\n[3/3] Case collection")
    from scripts.collect_cases import main as collect
    results = await collect(date_str, keywords)
    ok = sum(1 for r in results if r.get("success"))
    print(f"\nDone: {len(keywords)} keywords, {ok}/{len(results)} cases, {time.time()-t0:.1f}s")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=None)
    a = p.parse_args()
    asyncio.run(run(a.date or datetime.now().strftime("%Y%m%d")))
