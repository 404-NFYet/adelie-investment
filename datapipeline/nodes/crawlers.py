"""데이터 수집 노드: 뉴스/리포트 크롤링.

크롤러 실패는 비치명적 (빈 리스트 반환, 파이프라인 계속 진행).
"""

from __future__ import annotations

import datetime as dt
import logging
import time

from langsmith import traceable

from ..config import kst_today

logger = logging.getLogger(__name__)


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


def _recent_business_days(start_date: dt.date, limit: int) -> list[dt.date]:
    days: list[dt.date] = []
    cursor = start_date
    while len(days) < limit:
        if cursor.weekday() < 5:  # Mon-Fri
            days.append(cursor)
        cursor -= dt.timedelta(days=1)
    return days


def _build_crawl_status(
    *,
    requested_date: dt.date,
    used_date: dt.date | None,
    attempts: int,
    count: int,
    fallback_used: bool,
    error: str | None = None,
) -> dict[str, object]:
    return {
        "requested_date": requested_date.isoformat(),
        "used_date": used_date.isoformat() if used_date else None,
        "attempts": attempts,
        "count": count,
        "fallback_used": fallback_used,
        "error": error,
    }


# ── Mock 데이터 (지연 평가 — KST 기준 날짜 사용) ──


def _mock_news():
    today = kst_today().isoformat()
    return [
        {
            "title": "[Mock] 반도체 업황 개선 신호",
            "url": "https://example.com/mock-news-1",
            "source": "Mock Economy",
            "summary": "반도체 재고 조정이 마무리 국면에 접어들었어요.",
            "published_date": today,
        },
        {
            "title": "[Mock] AI 관련주 상승세",
            "url": "https://example.com/mock-news-2",
            "source": "Mock Finance",
            "summary": "AI 인프라 투자 확대로 관련 종목이 강세를 보이고 있어요.",
            "published_date": today,
        },
    ]


def _mock_reports():
    today = kst_today().isoformat()
    return [
        {
            "title": "[Mock] 산업 전망 리포트",
            "source": "Mock Securities",
            "summary": "2026년 반도체 업황은 하반기 회복이 예상돼요.",
            "date": today,
            "firm": "Mock Securities",
        },
    ]


@traceable(name="crawl_news", run_type="tool",
           metadata={"phase": "data_collection", "phase_name": "데이터 수집", "step": 1})
def crawl_news_node(state: dict) -> dict:
    """뉴스 RSS 크롤링."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] crawl_news")

    backend = state.get("backend", "live")
    market = state.get("market", "KR")

    if backend == "mock":
        mock_news = _mock_news()
        logger.info("  crawl_news mock: %d건", len(mock_news))
        return {
            "raw_news": mock_news,
            "crawl_news_status": _build_crawl_status(
                requested_date=kst_today(),
                used_date=kst_today(),
                attempts=1,
                count=len(mock_news),
                fallback_used=False,
            ),
            "metrics": _update_metrics(state, "crawl_news", time.time() - node_start),
        }

    from ..data_collection.news_crawler import crawl_news, to_news_items

    requested_date = kst_today()
    attempt_dates = _recent_business_days(requested_date, 3)
    attempts = 0
    last_error = ""

    for attempt_date in attempt_dates:
        attempts += 1
        try:
            raw_items = crawl_news(attempt_date, market=market)
            news_items = to_news_items(raw_items)
        except Exception as e:
            last_error = str(e)
            logger.warning("  crawl_news 실패 (attempt %d/%d, date=%s): %s", attempts, len(attempt_dates), attempt_date, e)
            continue

        if news_items:
            fallback_used = attempt_date != requested_date
            logger.info(
                "  crawl_news 완료: %d건 (requested=%s, used=%s, attempts=%d)",
                len(news_items),
                requested_date,
                attempt_date,
                attempts,
            )
            return {
                "raw_news": news_items,
                "crawl_news_status": _build_crawl_status(
                    requested_date=requested_date,
                    used_date=attempt_date,
                    attempts=attempts,
                    count=len(news_items),
                    fallback_used=fallback_used,
                ),
                "metrics": _update_metrics(state, "crawl_news", time.time() - node_start),
            }
        logger.warning(
            "  crawl_news 데이터 없음 (attempt %d/%d, date=%s)",
            attempts,
            len(attempt_dates),
            attempt_date,
        )

    error_msg = last_error or "lookback 3영업일 내 뉴스 데이터가 없습니다."
    return {
        "raw_news": [],
        "crawl_news_status": _build_crawl_status(
            requested_date=requested_date,
            used_date=None,
            attempts=attempts,
            count=0,
            fallback_used=attempts > 1,
            error=error_msg,
        ),
        "metrics": _update_metrics(state, "crawl_news", time.time() - node_start, "failed_nonfatal"),
    }


@traceable(name="crawl_research", run_type="tool",
           metadata={"phase": "data_collection", "phase_name": "데이터 수집", "step": 2})
def crawl_research_node(state: dict) -> dict:
    """Naver Finance 리포트 크롤링 + PDF 요약."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] crawl_research")

    backend = state.get("backend", "live")

    if backend == "mock":
        mock_reports = _mock_reports()
        logger.info("  crawl_research mock: %d건", len(mock_reports))
        return {
            "raw_reports": mock_reports,
            "crawl_research_status": _build_crawl_status(
                requested_date=kst_today(),
                used_date=kst_today(),
                attempts=1,
                count=len(mock_reports),
                fallback_used=False,
            ),
            "metrics": _update_metrics(state, "crawl_research", time.time() - node_start),
        }

    from ..data_collection.research_crawler import crawl_research, to_report_items

    requested_date = kst_today()
    attempt_dates = _recent_business_days(requested_date, 3)
    attempts = 0
    last_error = ""

    for attempt_date in attempt_dates:
        attempts += 1
        try:
            raw_items = crawl_research(attempt_date)
            report_items = to_report_items(raw_items)
        except Exception as e:
            last_error = str(e)
            logger.warning(
                "  crawl_research 실패 (attempt %d/%d, date=%s): %s",
                attempts,
                len(attempt_dates),
                attempt_date,
                e,
            )
            continue

        if report_items:
            fallback_used = attempt_date != requested_date
            logger.info(
                "  crawl_research 완료: %d건 (requested=%s, used=%s, attempts=%d)",
                len(report_items),
                requested_date,
                attempt_date,
                attempts,
            )
            return {
                "raw_reports": report_items,
                "crawl_research_status": _build_crawl_status(
                    requested_date=requested_date,
                    used_date=attempt_date,
                    attempts=attempts,
                    count=len(report_items),
                    fallback_used=fallback_used,
                ),
                "metrics": _update_metrics(state, "crawl_research", time.time() - node_start),
            }
        logger.warning(
            "  crawl_research 데이터 없음 (attempt %d/%d, date=%s)",
            attempts,
            len(attempt_dates),
            attempt_date,
        )

    error_msg = last_error or "lookback 3영업일 내 리포트 데이터가 없습니다."
    return {
        "raw_reports": [],
        "crawl_research_status": _build_crawl_status(
            requested_date=requested_date,
            used_date=None,
            attempts=attempts,
            count=0,
            fallback_used=attempts > 1,
            error=error_msg,
        ),
        "metrics": _update_metrics(state, "crawl_research", time.time() - node_start, "failed_nonfatal"),
    }
