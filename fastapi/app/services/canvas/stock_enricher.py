"""종목 데이터 통합 수집 — pykrx + DART + FDR 병렬 조회.

기존 stock_resolver, investment_intel의 데이터를 통합하고,
DART 주요주주/최근공시를 추가하여 풍부한 종목 정보를 제공합니다.
Redis 캐시 (TTL 4h)로 중복 조회를 방지합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.investment_intel import (
    _ensure_dart_corp_cache,
    _resolve_dart_corp_code,
    collect_stock_intelligence,
)
from app.services.stock_resolver import (
    detect_stock_codes,
    fetch_stock_data_for_context,
    get_fundamentals_text,
)

logger = logging.getLogger("narrative_api.canvas.stock_enricher")

KST = timezone(timedelta(hours=9))
_CACHE_PREFIX = "stock:enriched"
_CACHE_TTL = 14400  # 4시간


async def enrich_stock(
    *,
    db: AsyncSession,
    stock_code: str,
    stock_name: str,
) -> dict[str, Any]:
    """종목 데이터 통합 수집 (캐시 우선).

    Args:
        db: DB 세션
        stock_code: 종목 코드 (6자리)
        stock_name: 종목명

    Returns:
        통합 종목 정보 dict
    """
    # Redis 캐시 확인
    cache_key = f"{_CACHE_PREFIX}:{stock_code}"
    try:
        from app.services import get_redis_cache
        redis = await get_redis_cache()
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
    except Exception:
        redis = None

    # 병렬 수집
    result = await _collect_all(db, stock_code, stock_name)

    # Redis 캐시 저장
    try:
        if redis and result:
            await redis.set(
                cache_key,
                json.dumps(result, ensure_ascii=False, default=str),
                ex=_CACHE_TTL,
            )
    except Exception as e:
        logger.warning("Stock enrichment cache write failed: %s", e)

    return result


async def _collect_all(
    db: AsyncSession,
    stock_code: str,
    stock_name: str,
) -> dict[str, Any]:
    """모든 소스에서 병렬 수집."""
    detected = [(stock_name, stock_code)]

    tasks = {
        "intelligence": collect_stock_intelligence(db, None, detected),
        "price": asyncio.to_thread(fetch_stock_data_for_context, [stock_code]),
        "major_shareholders": _fetch_major_shareholders(db, stock_code, stock_name),
        "recent_disclosures": _fetch_recent_disclosures(db, stock_code, stock_name),
    }

    results = {}
    gathered = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True,
    )

    for key, value in zip(tasks.keys(), gathered):
        if isinstance(value, Exception):
            logger.warning("Stock enrichment [%s] failed: %s", key, value)
            results[key] = None
        else:
            results[key] = value

    # 결과 통합
    enriched: dict[str, Any] = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "collected_at": datetime.now(KST).isoformat(),
    }

    # intelligence 결과
    intel = results.get("intelligence")
    if isinstance(intel, tuple) and len(intel) == 3:
        enriched["context"] = intel[0]
        enriched["sources"] = intel[1]
        enriched["dart_metrics"] = intel[2]
    else:
        enriched["context"] = ""
        enriched["sources"] = []
        enriched["dart_metrics"] = {}

    # 주가 데이터
    price = results.get("price")
    if isinstance(price, tuple) and len(price) == 2:
        enriched["price_context"] = price[0]
        enriched["chart_data"] = price[1]
    else:
        enriched["price_context"] = ""
        enriched["chart_data"] = {}

    # 주요주주
    enriched["major_shareholders"] = results.get("major_shareholders") or []

    # 최근 공시
    enriched["recent_disclosures"] = results.get("recent_disclosures") or []

    # FDR 펀더멘탈 (동기 함수)
    try:
        fundamentals = get_fundamentals_text(stock_code)
        enriched["fundamentals"] = fundamentals
    except Exception:
        enriched["fundamentals"] = None

    return enriched


async def _fetch_major_shareholders(
    db: AsyncSession,
    stock_code: str,
    stock_name: str,
) -> list[dict[str, Any]]:
    """DART 주요주주현황 조회 (hyslrSttus.json).

    Returns:
        주요주주 목록 [{name, shares, ratio, ...}, ...]
    """
    settings = get_settings()
    api_key = (settings.OPEN_DART_API_KEY or "").strip()
    if not api_key:
        return []

    corp_code = await _resolve_dart_corp_code(db, api_key, stock_code, stock_name)
    if not corp_code:
        return []

    url = "https://opendart.fss.or.kr/api/hyslrSttus.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(datetime.now(KST).year - 1),
        "reprt_code": "11011",  # 사업보고서
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if str(data.get("status")) != "000":
            return []

        items = data.get("list", [])
        shareholders = []
        for item in items[:10]:  # 상위 10명
            shareholders.append({
                "name": item.get("nm", ""),
                "relation": item.get("relate", ""),
                "shares_begin": item.get("bsis_posesn_stock_co", ""),
                "shares_end": item.get("trmend_posesn_stock_co", ""),
                "ratio": item.get("trmend_posesn_stock_qota_rt", ""),
            })
        return shareholders

    except Exception as e:
        logger.warning("DART 주요주주 조회 실패 [%s]: %s", stock_code, e)
        return []


async def _fetch_recent_disclosures(
    db: AsyncSession,
    stock_code: str,
    stock_name: str,
    count: int = 3,
) -> list[dict[str, Any]]:
    """DART 최근 공시 목록 조회 (list.json).

    Args:
        count: 조회할 공시 수 (기본 3건)

    Returns:
        공시 목록 [{title, date, url, type}, ...]
    """
    settings = get_settings()
    api_key = (settings.OPEN_DART_API_KEY or "").strip()
    if not api_key:
        return []

    corp_code = await _resolve_dart_corp_code(db, api_key, stock_code, stock_name)
    if not corp_code:
        return []

    # 최근 90일 공시 조회
    end_date = datetime.now(KST)
    begin_date = end_date - timedelta(days=90)

    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": begin_date.strftime("%Y%m%d"),
        "end_de": end_date.strftime("%Y%m%d"),
        "page_count": str(count),
        "sort": "date",
        "sort_mth": "desc",
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if str(data.get("status")) != "000":
            return []

        items = data.get("list", [])
        disclosures = []
        for item in items[:count]:
            rcept_no = item.get("rcept_no", "")
            disclosures.append({
                "title": item.get("report_nm", ""),
                "date": item.get("rcept_dt", ""),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else "",
                "type": item.get("pblntf_ty", ""),
                "submitter": item.get("flr_nm", ""),
            })
        return disclosures

    except Exception as e:
        logger.warning("DART 최근공시 조회 실패 [%s]: %s", stock_code, e)
        return []
