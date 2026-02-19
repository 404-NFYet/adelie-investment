"""Backfill missing/invalid icon_key in daily_briefings.top_keywords.

Usage:
  python fastapi/scripts/backfill_daily_briefing_icon_keys.py --dry-run
  python fastapi/scripts/backfill_daily_briefing_icon_keys.py --date-from 2026-02-01 --date-to 2026-02-29
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime
import json
import os
from pathlib import Path

import asyncpg

ROOT_DIR = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT_DIR))

from datapipeline.constants.home_icons import backfill_top_keywords_icon_keys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill daily_briefings.top_keywords icon_key")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not update DB")
    parser.add_argument("--date-from", type=str, default=None, help="YYYY-MM-DD inclusive")
    parser.add_argument("--date-to", type=str, default=None, help="YYYY-MM-DD inclusive")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit (0 means no limit)")
    return parser.parse_args()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def normalize_db_url(db_url: str) -> str:
    return db_url.replace("+asyncpg", "")


async def run_backfill(
    *,
    dry_run: bool,
    date_from: date | None,
    date_to: date | None,
    limit: int = 0,
) -> tuple[int, int]:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    conn = await asyncpg.connect(normalize_db_url(db_url))
    try:
        clauses: list[str] = ["top_keywords IS NOT NULL"]
        params: list[object] = []

        if date_from:
            clauses.append(f"briefing_date >= ${len(params) + 1}")
            params.append(date_from)
        if date_to:
            clauses.append(f"briefing_date <= ${len(params) + 1}")
            params.append(date_to)

        query = (
            "SELECT id, briefing_date, top_keywords "
            "FROM daily_briefings "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY briefing_date DESC"
        )
        if limit and limit > 0:
            query += f" LIMIT {int(limit)}"

        rows = await conn.fetch(query, *params)

        scanned = 0
        updated_rows = 0
        updated_keywords = 0

        for row in rows:
            scanned += 1
            payload = row["top_keywords"]
            if isinstance(payload, str):
                payload = json.loads(payload)

            patched_payload, changed = backfill_top_keywords_icon_keys(payload)
            if changed <= 0:
                continue

            updated_rows += 1
            updated_keywords += changed
            print(
                f"[{row['briefing_date']}] briefing_id={row['id']} "
                f"changed_keywords={changed}"
            )
            if not dry_run:
                await conn.execute(
                    "UPDATE daily_briefings SET top_keywords = $1::jsonb WHERE id = $2",
                    json.dumps(patched_payload, ensure_ascii=False),
                    row["id"],
                )

        print(
            f"done: scanned={scanned}, "
            f"updated_rows={updated_rows}, updated_keywords={updated_keywords}, dry_run={dry_run}"
        )
        return updated_rows, updated_keywords
    finally:
        await conn.close()


async def main() -> None:
    args = parse_args()
    date_from = parse_date(args.date_from)
    date_to = parse_date(args.date_to)
    await run_backfill(
        dry_run=args.dry_run,
        date_from=date_from,
        date_to=date_to,
        limit=args.limit,
    )


if __name__ == "__main__":
    asyncio.run(main())
