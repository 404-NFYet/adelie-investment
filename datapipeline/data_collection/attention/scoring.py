"""6-proxy Attention Score 계산.

Proxy:
1. Abnormal Volume: log1p(당일거래량/252일평균) → z-score
2. Extreme Return: |전일수익률| → z-score
3. Past 12M Return: 252일 수익률(skip 21일) → z-score
4. Nearness 52W High: 현재가/52주최고 → z-score
5. Nearness Hist High: 현재가/역대최고(5년) → z-score
6. Media Coverage: log1p(Google News 7일 기사수) → z-score
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import FinanceDataReader as fdr
import pandas as pd
from tqdm import tqdm

from .media import fetch_google_news_coverage


@dataclass
class AttentionConfig:
    market: str = "KR"
    recency_days: int = 7
    volume_lookback_days: int = 252
    past_return_lookback_days: int = 252
    past_return_skip_days: int = 21
    historical_years: int = 5


def _get_col(df: pd.DataFrame, primary: str, fallback: str) -> Optional[str]:
    if primary in df.columns:
        return primary
    if fallback in df.columns:
        return fallback
    return None


def _fetch_ohlcv(symbol: str, start: str, end: str) -> Optional[pd.DataFrame]:
    try:
        df = fdr.DataReader(symbol, start, end)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return df.sort_index()


def _zscore(values: List[Optional[float]]) -> List[Optional[float]]:
    """Population z-score (std=0이면 0 반환)."""
    cleaned = [v for v in values if v is not None and not math.isnan(v)]
    if not cleaned:
        return [None for _ in values]
    mean = sum(cleaned) / len(cleaned)
    var = sum((v - mean) ** 2 for v in cleaned) / len(cleaned)
    std = math.sqrt(var)
    if std == 0:
        return [0.0 if v is not None and not math.isnan(v) else None for v in values]
    return [
        (v - mean) / std if v is not None and not math.isnan(v) else None
        for v in values
    ]


def _percentile_rank(values: List[Optional[float]], value: Optional[float]) -> Optional[float]:
    if value is None or math.isnan(value):
        return None
    cleaned = [v for v in values if v is not None and not math.isnan(v)]
    if not cleaned:
        return None
    count = sum(1 for v in cleaned if v <= value)
    return round(count / len(cleaned) * 100, 1)


def _calc_metrics(df: pd.DataFrame, config: AttentionConfig) -> Dict[str, Optional[float]]:
    """종목별 6개 raw proxy 계산."""
    close_col = _get_col(df, "Close", "close")
    high_col = _get_col(df, "High", "high")
    vol_col = _get_col(df, "Volume", "volume")
    if not close_col:
        return {}

    closes = df[close_col]
    highs = df[high_col] if high_col else closes
    vols = df[vol_col] if vol_col else None

    metrics: Dict[str, Optional[float]] = {
        "abnormal_volume_ratio": None,
        "prev_day_return": None,
        "past_return_12m_ex1m": None,
        "nearness_52w_high": None,
        "nearness_hist_high": None,
    }

    # Proxy 1: Abnormal Volume
    if vols is not None and len(vols) >= config.volume_lookback_days + 1:
        vol_now = vols.iloc[-1]
        vol_base = vols.iloc[-(config.volume_lookback_days + 1):-1].mean()
        if vol_base and vol_base > 0:
            metrics["abnormal_volume_ratio"] = float(vol_now / vol_base)

    # Proxy 2: Extreme Return (전일 수익률)
    if len(closes) >= 3:
        prev_close = closes.iloc[-2]
        prev_prev_close = closes.iloc[-3]
        if prev_prev_close > 0:
            metrics["prev_day_return"] = float(prev_close / prev_prev_close - 1)

    # Proxy 3: Past 12M Return (skip 1M)
    need = config.past_return_lookback_days + config.past_return_skip_days + 1
    if len(closes) >= need:
        past_start = closes.iloc[-(config.past_return_lookback_days + config.past_return_skip_days)]
        past_end = closes.iloc[-(config.past_return_skip_days + 1)]
        if past_start > 0:
            metrics["past_return_12m_ex1m"] = float(past_end / past_start - 1)

    # Proxy 4: Nearness 52W High
    if len(highs) >= config.volume_lookback_days:
        high_52w = highs.iloc[-config.volume_lookback_days:].max()
        price_now = closes.iloc[-1]
        if high_52w > 0:
            metrics["nearness_52w_high"] = float(price_now / high_52w)

    # Proxy 5: Nearness Historical High (전체 기간)
    hist_high = highs.max()
    price_now = closes.iloc[-1]
    if hist_high and hist_high > 0:
        metrics["nearness_hist_high"] = float(price_now / hist_high)

    return metrics


def compute_attention_scores(
    stocks: List[dict],
    market: str = "KR",
    recency_days: int = 7,
    historical_years: int = 5,
    media_counts: Dict[str, int] | None = None,
    use_google_news: bool = True,
    news_workers: int = 1,
    show_progress: bool = True,
) -> List[dict]:
    """6개 proxy z-score 기반 attention score 계산."""
    config = AttentionConfig(
        market=market,
        recency_days=recency_days,
        historical_years=historical_years,
    )

    # Proxy 6: Media Coverage
    if media_counts is not None:
        news_counts = media_counts
    elif use_google_news:
        news_counts = fetch_google_news_coverage(
            stocks,
            market=market,
            recency_days=recency_days,
            max_workers=news_workers,
            show_progress=show_progress,
        )
    else:
        news_counts = {(s.get("symbol") or "").strip(): 0 for s in stocks}

    end = datetime.now()
    start = end - timedelta(days=365 * historical_years)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    rows: List[dict] = []
    iterator = stocks
    if show_progress:
        iterator = tqdm(stocks, desc=f"Attention OHLCV ({market})", unit="stock")
    for s in iterator:
        symbol = (s.get("symbol") or "").strip()
        name = (s.get("name") or "").strip()
        if not symbol:
            continue

        df = _fetch_ohlcv(symbol, start_str, end_str)
        if df is None or df.empty:
            continue

        metrics = _calc_metrics(df, config)
        metrics.update(
            {
                "symbol": symbol,
                "name": name,
                "media_coverage_count_7d": int(news_counts.get(symbol, 0)),
            }
        )
        rows.append(metrics)

    # z-score 계산 (각 proxy별)
    vol_vals = [
        math.log1p(r["abnormal_volume_ratio"]) if r.get("abnormal_volume_ratio") is not None else None
        for r in rows
    ]
    ret_vals = [abs(r["prev_day_return"]) if r.get("prev_day_return") is not None else None for r in rows]
    past_vals = [r.get("past_return_12m_ex1m") for r in rows]
    near_52_vals = [r.get("nearness_52w_high") for r in rows]
    near_hist_vals = [r.get("nearness_hist_high") for r in rows]
    media_vals = [math.log1p(r.get("media_coverage_count_7d", 0)) for r in rows]

    z_vol = _zscore(vol_vals)
    z_ret = _zscore(ret_vals)
    z_past = _zscore(past_vals)
    z_52 = _zscore(near_52_vals)
    z_hist = _zscore(near_hist_vals)
    z_media = _zscore(media_vals)

    # Composite score = 유효 z-score 평균
    score_vals: List[Optional[float]] = []
    for i, r in enumerate(rows):
        components = {
            "z_abnormal_volume": z_vol[i],
            "z_extreme_return": z_ret[i],
            "z_past_return": z_past[i],
            "z_near_52w_high": z_52[i],
            "z_near_hist_high": z_hist[i],
            "z_media_coverage": z_media[i],
        }
        valid = [v for v in components.values() if v is not None]
        score = sum(valid) / len(valid) if valid else None
        r["attention_components"] = components
        r["attention_score"] = round(score, 4) if score is not None else None
        score_vals.append(score)

    # Percentile rank
    for r in rows:
        r["attention_percentile"] = _percentile_rank(score_vals, r.get("attention_score"))

    return rows
