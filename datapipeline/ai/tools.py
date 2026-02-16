"""Financial Tools for Chart Agent.

DART(Corporate), ECOS(Exchange Rate), and Web Search tools.
"""

import logging
import os
from typing import Optional, Any

import requests

from ..config import DART_API_KEY, ECOS_API_KEY, OPENAI_API_KEY
from .multi_provider_client import get_multi_provider_client

logger = logging.getLogger(__name__)
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_WEB_SEARCH_MODEL = os.getenv("OPENAI_WEB_SEARCH_MODEL", "gpt-5-mini")

# ── DART (Korean Corporate Data) ──

def get_corp_financials(corp_name: str, year: Optional[int] = None) -> dict:
    """
    Retrieves financial information (Revenue, Operating Income, Net Income) for a specific Korean corporation.
    
    Args:
        corp_name: Name of the corporation (e.g., "삼성전자").
        year: Target year (e.g., 2024). If None, returns the latest available data.
        
    Returns:
        JSON dictionary containing financial data.
    """
    logger.info(f"[Tool] get_corp_financials: {corp_name}, year={year}")
    
    if not DART_API_KEY:
        return {"error": "DART_API_KEY not configured", "mock_data": _get_mock_financials(corp_name, year)}

    # TODO: Real DART API implementation would require corp_code lookup.
    # For this MVP, we will try to search or just return mock if complex lookup is needed.
    # Since we don't have the corp_code map loaded, we will fallback to Mock or Web Search for now
    # unless we implement the full corp_code logic.
    
    # Real logic placeholder
    # 1. Get corp_code from name
    # 2. Call /fnlttSinglAcnt.xml or .json
    
    # Returning mock for stability until corp_code map is integrated
    return _get_mock_financials(corp_name, year)


def _get_mock_financials(corp_name: str, year: Optional[int]) -> dict:
    base_year = year or 2025
    if "삼성" in corp_name:
        return {
            "corp_name": corp_name,
            "year": base_year,
            "data": {
                "sales": "300000000000000",
                "operating_income": "6000000000000",
                "net_income": "5500000000000"
            },
            "unit": "KRW",
            "source": "DART_Mock"
        }
    return {"error": "Data not found", "corp_name": corp_name}


# ── ECOS (Bank of Korea Exchange Rate) ──

def get_exchange_rate(target_date: str) -> dict:
    """
    Retrieves KRW/USD exchange rate for a specific date from BOK ECOS.
    
    Args:
        target_date: Date string in 'YYYYMMDD' format (e.g., "20240101").
        
    Returns:
        JSON dictionary with exchange rate.
    """
    logger.info(f"[Tool] get_exchange_rate: {target_date}")
    
    if not ECOS_API_KEY:
        return {"date": target_date, "rate": 1350.0, "source": "ECOS_Mock"}

    # Placeholder for real ECOS API call
    # url = f"http://ecos.bok.or.kr/api/StatisticSearch/{ECOS_API_KEY}/json/kr/1/10/731Y001/D/{target_date}/{target_date}/0000001"
    
    return {"date": target_date, "rate": 1345.5, "source": "ECOS_Mock_KeyPresent"}


# ── Web Search (Perplexity/Tavily) ──

def _extract_openai_output_text(resp_json: dict[str, Any]) -> str:
    for item in resp_json.get("output", []) or []:
        if item.get("type") != "message" or item.get("status") != "completed":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                return str(content.get("text"))
    return ""


def _extract_openai_web_sources(resp_json: dict[str, Any]) -> list[dict[str, Any]]:
    source_rows: list[dict[str, Any]] = []
    for item in resp_json.get("output", []) or []:
        if item.get("type") != "web_search_call":
            continue
        action = item.get("action")
        if not isinstance(action, dict):
            continue
        for source in action.get("sources", []) or []:
            if isinstance(source, dict):
                source_rows.append(source)
    return source_rows


def _search_with_openai_web_search(query: str) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY not configured"}

    prompt = (
        "아래 질의에 대해 차트 생성용 정량 데이터 위주로 조사하세요.\n"
        "- 수치, 기간, 단위를 가능한 한 명시\n"
        "- 근거 출처를 함께 제시\n"
        f"\n질의: {query}"
    )
    payload = {
        "model": OPENAI_WEB_SEARCH_MODEL,
        "tools": [{"type": "web_search"}],
        "tool_choice": "auto",
        "include": ["web_search_call.action.sources"],
        "input": prompt,
        "max_output_tokens": 1600,
    }
    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    if not response.ok:
        return {
            "error": f"OpenAI web_search error {response.status_code}",
            "detail": response.text[:1200],
        }

    data = response.json()
    output_text = _extract_openai_output_text(data)
    source_rows = _extract_openai_web_sources(data)
    return {
        "result": output_text,
        "source": "OpenAI_WebSearch",
        "model": OPENAI_WEB_SEARCH_MODEL,
        "sources": source_rows,
        "source_count": len(source_rows),
    }


def search_web_for_chart_data(query: str) -> dict:
    """
    Searches the web for quantitative data suitable for charting.
    Use this when specific API tools (DART, ECOS) are insufficient.
    
    Args:
        query: Search query (e.g., "US Treasury 10Y yield chart data 2024").
    
    Returns:
        JSON dictionary with search results/summary.
    """
    logger.info(f"[Tool] search_web_for_chart_data: {query}")

    # 1) OpenAI Responses API web_search 우선
    try:
        openai_result = _search_with_openai_web_search(query)
        if not openai_result.get("error"):
            return openai_result
        logger.warning(f"OpenAI web_search failed: {openai_result.get('error')}")
    except Exception as e:
        logger.error(f"OpenAI web_search exception: {e}")

    # 2) Perplexity 폴백
    client = get_multi_provider_client()

    if "perplexity" in client.providers:
        messages = [
            {"role": "system", "content": "You are a research assistant. Find precise quantitative data for the user's query. Return the data in a structured format (JSON-like) if possible, with sources."},
            {"role": "user", "content": query}
        ]
        try:
            result = client.chat_completion(
                provider="perplexity",
                model="sonar-pro", # or sonar-reasoning
                messages=messages,
                temperature=0.1
            )
            content = result["choices"][0]["message"]["content"]
            return {"result": content, "source": "Perplexity"}
        except Exception as e:
            logger.error(f"Perplexity search failed: {e}")
            return {"error": str(e)}

    # 3) 최종 Mock 폴백
    return {
        "result": f"Simulated search result for '{query}': Found trend data [10, 20, 15, 25] for 2024.",
        "source": "Mock_Search"
    }
