"""시가총액 기준 유니버스 로딩."""

from __future__ import annotations

from typing import List

import FinanceDataReader as fdr
import requests


def _get_col(df, primary: str, fallback: str) -> str | None:
    if primary in df.columns:
        return primary
    if fallback in df.columns:
        return fallback
    return None


def _parse_marketcap(value: str | None) -> int | None:
    if not value:
        return None
    s = str(value).strip().upper()
    if s in {"N/A", "NA", "--", ""}:
        return None
    mult = 1
    if s.endswith("T"):
        mult = 1_000_000_000_000
        s = s[:-1]
    elif s.endswith("B"):
        mult = 1_000_000_000
        s = s[:-1]
    elif s.endswith("M"):
        mult = 1_000_000
        s = s[:-1]
    s = s.replace("$", "").replace(",", "")
    try:
        return int(float(s) * mult)
    except Exception:
        return None


def _fetch_nasdaq_rows(limit: int, offset: int) -> List[dict]:
    url = "https://api.nasdaq.com/api/screener/stocks"
    params = {
        "tableonly": "true",
        "limit": limit,
        "offset": offset,
        "sortColumn": "marketCap",
        "sortOrder": "desc",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/market-activity/stocks/screener",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    table = data.get("data", {}).get("table", {})
    return table.get("rows", []) or []


def _load_us_top_marketcap(top_n: int) -> List[dict]:
    batch = max(200, top_n * 2)
    offset = 0
    rows: List[dict] = []

    while len(rows) < top_n:
        chunk = _fetch_nasdaq_rows(batch, offset)
        if not chunk:
            break
        for item in chunk:
            cap = _parse_marketcap(item.get("marketCap"))
            if cap is None:
                continue
            rows.append(
                {
                    "symbol": str(item.get("symbol", "")).strip(),
                    "name": str(item.get("name", "")).strip(),
                    "marketCap": cap,
                }
            )
        offset += batch
        if offset > 5000:
            break

    rows = [r for r in rows if r.get("symbol")]
    rows = sorted(rows, key=lambda x: x["marketCap"], reverse=True)[:top_n]
    return [{"symbol": r["symbol"], "name": r["name"]} for r in rows]


def load_universe_top_marketcap(market: str, top_n: int) -> List[dict]:
    """시장별 시가총액 상위 N종목 로딩."""
    if market == "KR":
        listing = fdr.StockListing("KRX")
        if "Marcap" not in listing.columns:
            raise ValueError("KRX listing has no Marcap column")
        top = listing.sort_values("Marcap", ascending=False).head(top_n)
        return [
            {"symbol": str(r["Code"]).strip(), "name": str(r.get("Name", "")).strip()}
            for _, r in top.iterrows()
            if str(r.get("Code", "")).strip()
        ]

    return _load_us_top_marketcap(top_n)
