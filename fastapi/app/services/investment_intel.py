"""Stock intelligence helpers for tutor stock-mode responses.

Collects internal briefing/report context and OpenDART financial facts,
then normalizes source metadata for canvas rendering.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import zipfile
from datetime import datetime
from typing import Any, Optional
from xml.etree import ElementTree

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.briefing import BriefingStock, DailyBriefing
from app.models.report import BrokerReport
from app.models.stock_listing import StockListing

logger = logging.getLogger("narrative_api.investment_intel")

_DART_CORP_BY_NAME: dict[str, str] = {}
_DART_CORP_BY_STOCK: dict[str, str] = {}
_DART_CACHE_READY = False
_DART_CACHE_LOCK = asyncio.Lock()


def _clean_name(value: str) -> str:
    return re.sub(r"[\s\(\)\[\]\.\-]", "", str(value or "").lower())


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    raw = str(value).replace(",", "").strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _pick_account_value(items: list[dict[str, Any]], *names: str) -> Optional[int]:
    for row in items:
        account_name = str(row.get("account_nm", "")).strip()
        if account_name in names:
            return _to_int(row.get("thstrm_amount"))
    return None


def parse_context_envelope(context_text: Optional[str]) -> dict[str, Any]:
    if not context_text or not isinstance(context_text, str):
        return {}
    try:
        payload = json.loads(context_text)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def extract_stock_target(
    context_text: Optional[str],
    detected_stocks: list[tuple[str, str]],
) -> tuple[Optional[str], Optional[str]]:
    payload = parse_context_envelope(context_text)
    context = payload.get("context") if isinstance(payload.get("context"), dict) else payload

    stock_code = str(context.get("stock_code", "")).strip() if isinstance(context, dict) else ""
    stock_name = str(context.get("stock_name", "")).strip() if isinstance(context, dict) else ""

    if not stock_code and detected_stocks:
        stock_name = stock_name or detected_stocks[0][0]
        stock_code = detected_stocks[0][1]

    return (stock_code or None, stock_name or None)


async def _ensure_dart_corp_cache(api_key: str) -> None:
    global _DART_CACHE_READY
    if _DART_CACHE_READY:
        return

    async with _DART_CACHE_LOCK:
        if _DART_CACHE_READY:
            return

        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, params={"crtfc_key": api_key})
            response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_name = zf.namelist()[0]
            xml_data = zf.read(xml_name)

        root = ElementTree.fromstring(xml_data)
        by_name: dict[str, str] = {}
        by_stock: dict[str, str] = {}
        for node in root.findall("list"):
            corp_code = (node.findtext("corp_code") or "").strip()
            corp_name = (node.findtext("corp_name") or "").strip()
            stock_code = (node.findtext("stock_code") or "").strip()
            if not corp_code or not corp_name:
                continue
            by_name[_clean_name(corp_name)] = corp_code
            if stock_code:
                by_stock[stock_code] = corp_code

        _DART_CORP_BY_NAME.clear()
        _DART_CORP_BY_STOCK.clear()
        _DART_CORP_BY_NAME.update(by_name)
        _DART_CORP_BY_STOCK.update(by_stock)
        _DART_CACHE_READY = True


async def _resolve_dart_corp_code(
    db: AsyncSession,
    api_key: str,
    stock_code: Optional[str],
    stock_name: Optional[str],
) -> Optional[str]:
    try:
        await _ensure_dart_corp_cache(api_key)
    except Exception as e:
        logger.warning("OpenDART corp cache load failed: %s", e)
        return None

    if stock_code and stock_code in _DART_CORP_BY_STOCK:
        return _DART_CORP_BY_STOCK[stock_code]

    if stock_name:
        cleaned = _clean_name(stock_name)
        if cleaned in _DART_CORP_BY_NAME:
            return _DART_CORP_BY_NAME[cleaned]

    if stock_code:
        listing = await db.execute(
            select(StockListing).where(StockListing.stock_code == stock_code)
        )
        row = listing.scalar_one_or_none()
        if row:
            cleaned = _clean_name(row.stock_name)
            if cleaned in _DART_CORP_BY_NAME:
                return _DART_CORP_BY_NAME[cleaned]

    return None


async def _collect_internal_stock_context(
    db: AsyncSession,
    stock_code: Optional[str],
    stock_name: Optional[str],
) -> tuple[str, list[dict[str, Any]]]:
    if not stock_code and not stock_name:
        return "", []

    lines: list[str] = []
    sources: list[dict[str, Any]] = []

    stmt = (
        select(BriefingStock, DailyBriefing)
        .join(DailyBriefing, DailyBriefing.id == BriefingStock.briefing_id)
        .order_by(desc(DailyBriefing.briefing_date))
        .limit(8)
    )
    rows = (await db.execute(stmt)).all()

    matched_rows = []
    for brief_stock, daily in rows:
        if stock_code and brief_stock.stock_code == stock_code:
            matched_rows.append((brief_stock, daily))
            continue
        if stock_name and brief_stock.stock_name == stock_name:
            matched_rows.append((brief_stock, daily))

    for brief_stock, daily in matched_rows[:3]:
        day_label = daily.briefing_date.strftime("%Y-%m-%d")
        lines.append(
            f"- {day_label} 브리핑: {brief_stock.stock_name} {float(brief_stock.change_rate or 0):+.2f}%"
        )
        if brief_stock.catalyst:
            lines.append(f"  · 뉴스 촉매: {brief_stock.catalyst}")
        if brief_stock.selection_reason:
            lines.append(f"  · 분류: {brief_stock.selection_reason}")

        if brief_stock.catalyst_url:
            sources.append(
                {
                    "type": "news",
                    "source_kind": "internal",
                    "title": f"{brief_stock.stock_name} 촉매 뉴스",
                    "url": brief_stock.catalyst_url,
                    "content": brief_stock.catalyst or "",
                }
            )

        sources.append(
            {
                "type": "internal",
                "source_kind": "internal",
                "title": f"{brief_stock.stock_name} 브리핑 ({day_label})",
                "url": "",
                "content": daily.market_summary or "",
            }
        )

    report_rows = (
        await db.execute(select(BrokerReport).order_by(desc(BrokerReport.report_date)).limit(25))
    ).scalars().all()
    for report in report_rows:
        codes = report.stock_codes if isinstance(report.stock_codes, list) else []
        if stock_code and stock_code not in codes:
            continue
        if not stock_code and stock_name and stock_name not in (report.report_title or ""):
            continue

        sources.append(
            {
                "type": "report",
                "source_kind": "internal",
                "title": f"{report.broker_name} 리포트",
                "url": report.pdf_url or "",
                "content": report.report_title,
            }
        )
        if len(sources) >= 8:
            break

    if lines:
        context = "\n[내부 투자 인텔]\n" + "\n".join(lines[:8])
    else:
        context = ""

    return context, sources


async def _collect_dart_financial_context(
    db: AsyncSession,
    stock_code: Optional[str],
    stock_name: Optional[str],
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    settings = get_settings()
    api_key = (settings.OPEN_DART_API_KEY or "").strip()
    if not api_key:
        return "", [], {}

    corp_code = await _resolve_dart_corp_code(db, api_key, stock_code, stock_name)
    if not corp_code:
        return "", [], {}

    bsns_year = datetime.now().year - 1
    report_code = "11011"  # 사업보고서
    base_url = "https://opendart.fss.or.kr/api"
    metrics: dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=8.0) as client:
        fs_resp = await client.get(
            f"{base_url}/fnlttSinglAcntAll.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bsns_year": str(bsns_year),
                "reprt_code": report_code,
            },
        )
        fs_resp.raise_for_status()
        fs_data = fs_resp.json()

        if str(fs_data.get("status")) != "000":
            return "", [], {}

        rows = fs_data.get("list") if isinstance(fs_data.get("list"), list) else []
        revenue = _pick_account_value(rows, "매출액", "수익(매출액)")
        operating_income = _pick_account_value(rows, "영업이익")
        net_income = _pick_account_value(rows, "당기순이익", "당기순이익(손실)")
        total_assets = _pick_account_value(rows, "자산총계")
        total_liabilities = _pick_account_value(rows, "부채총계")

        metrics = {
            "year": bsns_year,
            "revenue": revenue,
            "operating_income": operating_income,
            "net_income": net_income,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
        }

        list_resp = await client.get(
            f"{base_url}/list.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bgn_de": f"{bsns_year}0101",
                "end_de": f"{bsns_year}1231",
                "pblntf_ty": "A",
                "page_count": "1",
            },
        )
        list_resp.raise_for_status()
        list_data = list_resp.json()
        rcp_no = None
        if str(list_data.get("status")) == "000":
            items = list_data.get("list") if isinstance(list_data.get("list"), list) else []
            if items:
                rcp_no = items[0].get("rcept_no")

    metric_lines = []
    if revenue is not None:
        metric_lines.append(f"- 매출액: {revenue:,}원")
    if operating_income is not None:
        metric_lines.append(f"- 영업이익: {operating_income:,}원")
    if net_income is not None:
        metric_lines.append(f"- 당기순이익: {net_income:,}원")
    if total_assets is not None:
        metric_lines.append(f"- 자산총계: {total_assets:,}원")
    if total_liabilities is not None:
        metric_lines.append(f"- 부채총계: {total_liabilities:,}원")

    if not metric_lines:
        return "", [], {}

    source_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp_no}" if rcp_no else "https://dart.fss.or.kr/"
    context = "\n[OpenDART 핵심 재무수치]\n" + "\n".join(metric_lines)
    sources = [
        {
            "type": "dart",
            "source_kind": "dart",
            "title": f"OpenDART {stock_name or stock_code or ''} 재무수치",
            "url": source_url,
            "content": f"{bsns_year}년 사업보고서 기준",
            "metrics": metrics,
        }
    ]
    return context, sources, metrics


def normalize_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kind_map = {
        "dart": "dart",
        "news": "news",
        "report": "internal",
        "internal": "internal",
        "stock_price": "internal",
        "financial": "internal",
        "glossary": "internal",
        "case": "internal",
        "web": "web",
    }
    normalized = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_type = str(source.get("type") or "internal")
        item = dict(source)
        item.setdefault("source_kind", kind_map.get(source_type, "internal"))
        item.setdefault("is_reachable", None)
        normalized.append(item)
    return normalized


async def annotate_reachable_links(sources: list[dict[str, Any]], max_checks: int = 6) -> list[dict[str, Any]]:
    if not sources:
        return []

    normalized = normalize_sources(sources)
    indexed_targets: list[tuple[int, str]] = []
    for idx, item in enumerate(normalized):
        url = str(item.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        indexed_targets.append((idx, url))

    async def _check(url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.4, follow_redirects=True) as client:
                head = await client.head(url)
                if head.status_code < 400:
                    return True
                get_resp = await client.get(url)
                return get_resp.status_code < 400
        except Exception:
            return False

    tasks = [asyncio.create_task(_check(url)) for _, url in indexed_targets[:max_checks]]
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for (idx, _), ok in zip(indexed_targets[:max_checks], results):
            normalized[idx]["is_reachable"] = bool(ok) if not isinstance(ok, Exception) else False

    return normalized


async def collect_stock_intelligence(
    db: AsyncSession,
    context_text: Optional[str],
    detected_stocks: list[tuple[str, str]],
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Collect stock-mode extra context and enriched source list."""
    stock_code, stock_name = extract_stock_target(context_text, detected_stocks)
    if not stock_code and not stock_name:
        return "", [], {}

    internal_context, internal_sources = await _collect_internal_stock_context(db, stock_code, stock_name)
    dart_context, dart_sources, dart_metrics = await _collect_dart_financial_context(db, stock_code, stock_name)

    composed = []
    if stock_name or stock_code:
        composed.append(f"[분석 대상] {stock_name or stock_code} ({stock_code or '코드 미확인'})")
    if internal_context:
        composed.append(internal_context)
    if dart_context:
        composed.append(dart_context)

    merged_sources = normalize_sources(internal_sources + dart_sources)

    return ("\n\n".join(composed)).strip(), merged_sources, dart_metrics
