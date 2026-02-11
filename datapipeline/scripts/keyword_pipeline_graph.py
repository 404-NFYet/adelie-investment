"""LangGraph 기반 키워드 생성 파이프라인.

순차 실행 스크립트를 LangGraph 노드 기반으로 재구성하여
- 각 단계별 실행 시간 추적
- LangSmith 자동 트래킹
- 에러 핸들링 및 재시도
- 모니터링 지표 수집
"""
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional, TypedDict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("keyword_pipeline")

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "fastapi"))

# 설정 상수
from datapipeline.scripts.pipeline_config import (
    ANALYSIS_TRUNCATION,
    API_TIMEOUT,
    FALLBACK_QUALITY_SCORE,
    FINAL_KEYWORDS,
    KOREAN_FINANCIAL_DOMAINS,
    MACRO_CONTEXT_BONUS,
    MAX_RETRIES,
    MIN_TRADE_VALUE,
    MIN_TRENDING,
    RETRY_BASE_DELAY,
    SECTOR_ANALYSIS_BONUS,
    SECTOR_ROTATION_BONUS,
    THEME_TARGET,
    TOP_CANDIDATES,
    TRENDING_TARGET,
)

# 기존 함수들 임포트
from datapipeline.scripts.seed_fresh_data_integrated import (
    SECTOR_ROTATION_MAP,
    calculate_quality_score,
    calculate_technical_indicators,
    calculate_trend_metrics,
    cluster_by_sector,
    determine_economic_cycle,
    fetch_multi_day_data,
    get_latest_trading_date,
    select_top_themes,
    select_top_trending,
)


# ============================================================
# 유틸리티
# ============================================================


def retry_with_backoff(func, max_retries=MAX_RETRIES, base_delay=RETRY_BASE_DELAY):
    """지수 백오프 재시도 래퍼."""

    def wrapper(*args, **kwargs):
        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries:
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"재시도 {attempt}/{max_retries} ({delay}s 대기): {e}")
                time.sleep(delay)

    return wrapper


def _update_metrics(state, node_name, elapsed, status="success"):
    """노드 실행 메트릭을 state에 기록."""
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


# ============================================================
# State 정의
# ============================================================


class KeywordPipelineState(TypedDict):
    """파이프라인 상태."""

    # Phase 1: Market data
    end_date_str: Optional[str]
    end_date_obj: Optional[datetime]
    raw_market_data: Optional[list]
    trending_stocks: Optional[list]

    # Phase 2: Sector clustering
    enriched_stocks: Optional[list]
    theme_clusters: Optional[list]
    selected_themes: Optional[list]

    # Phase 3: News matching (Perplexity catalysts)
    news_articles: Optional[list]
    stock_news_map: Optional[dict]

    # Phase 3-2: Sector/Macro analysis (Perplexity)
    sector_analyses: Optional[dict]  # sector → {analysis, citations}
    macro_context: Optional[dict]  # {analysis, citations, timestamp}

    # Phase 4: Keyword generation
    keyword_candidates: Optional[list]
    final_keywords: Optional[list]

    # Metadata
    openai_api_key: str
    error: Optional[str]
    metrics: Annotated[dict, lambda a, b: {**a, **b}]  # 병렬 노드 병합 지원


# ============================================================
# Node 함수들
# ============================================================


@traceable(name="collect_market_data", run_type="tool")
def collect_market_data_node(state: KeywordPipelineState) -> dict:
    """Phase 1-1: pykrx로 5일 시장 데이터 수집."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] collect_market_data")

    try:
        end_date_str, end_date_obj = get_latest_trading_date()
        logger.info(f"  최근 영업일: {end_date_str}")

        df_all = fetch_multi_day_data(end_date_str, days=5, min_trade_value=MIN_TRADE_VALUE)
        logger.info(f"  5일 데이터 수집: {len(df_all)}건 (거래대금 >= {MIN_TRADE_VALUE:,}원)")

        return {
            "end_date_str": end_date_str,
            "end_date_obj": end_date_obj,
            "raw_market_data": df_all,
            "metrics": _update_metrics(state, "collect_market_data", time.time() - node_start),
        }
    except Exception as e:
        logger.error(f"  시장 데이터 수집 실패: {e}")
        return {
            "error": f"Market data collection failed: {e}",
            "metrics": _update_metrics(state, "collect_market_data", time.time() - node_start, "failed"),
        }


@traceable(name="filter_trends", run_type="tool")
def filter_trends_node(state: KeywordPipelineState) -> dict:
    """Phase 1-2: 멀티데이 트렌드 필터링."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] filter_trends")

    try:
        df = state.get("raw_market_data")
        end_date_str = state.get("end_date_str")
        if df is None or end_date_str is None:
            return {"error": "raw_market_data 또는 end_date_str 누락"}

        trending = calculate_trend_metrics(df)
        logger.info(f"  트렌드 감지: {len(trending)}개 종목")

        if len(trending) < MIN_TRENDING:
            return {"error": f"트렌딩 종목 부족: {len(trending)}개 (최소 {MIN_TRENDING})"}

        # RSI/MACD 기술 지표 계산 (상위 후보 종목만)
        top_codes = [
            s["stock_code"]
            for s in sorted(trending, key=lambda x: abs(x["change_rate"]), reverse=True)[:TOP_CANDIDATES]
        ]
        indicators = {}
        try:
            indicators = calculate_technical_indicators(top_codes, end_date_str)
            logger.info(f"  기술 지표 계산: {len(indicators)}개 종목 (RSI/MACD)")
        except Exception as e:
            logger.warning(f"  기술 지표 계산 실패 (계속 진행): {e}")

        selected = select_top_trending(trending, target=TRENDING_TARGET, indicators=indicators)
        logger.info(f"  상위 {len(selected)}개 선택")

        # 종목명 추가
        from pykrx import stock as pykrx_stock

        for s in selected:
            try:
                s["stock_name"] = pykrx_stock.get_market_ticker_name(s["stock_code"])
            except Exception as e:
                logger.warning(f"  종목명 조회 실패 {s['stock_code']}: {e}")
                s["stock_name"] = s["stock_code"]

        return {
            "trending_stocks": selected,
            "metrics": _update_metrics(state, "filter_trends", time.time() - node_start),
        }
    except Exception as e:
        logger.error(f"  트렌드 필터링 실패: {e}")
        return {
            "error": f"Trend filtering failed: {e}",
            "metrics": _update_metrics(state, "filter_trends", time.time() - node_start, "failed"),
        }


@traceable(name="enrich_sectors", run_type="tool")
def enrich_sectors_node(state: KeywordPipelineState) -> dict:
    """Phase 2-1: 섹터 정보 enrichment."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] enrich_sectors")

    stocks = state.get("trending_stocks")
    if not stocks:
        return {"error": "trending_stocks 누락"}

    try:
        import asyncio

        from scripts.seed_fresh_data_integrated import enrich_with_sectors

        enriched = asyncio.run(enrich_with_sectors(stocks))
        logger.info(f"  섹터 정보 매핑: {len(enriched)}개")

        return {
            "enriched_stocks": enriched,
            "metrics": _update_metrics(state, "enrich_sectors", time.time() - node_start),
        }
    except Exception as e:
        logger.warning(f"  섹터 매핑 실패 (계속 진행): {e}")
        # 섹터 정보 없어도 계속 진행
        return {
            "enriched_stocks": stocks,
            "metrics": _update_metrics(state, "enrich_sectors", time.time() - node_start, "fallback"),
        }


@traceable(name="cluster_themes", run_type="tool")
def cluster_themes_node(state: KeywordPipelineState) -> dict:
    """Phase 2-2: 섹터별 테마 클러스터링."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] cluster_themes")

    stocks = state.get("enriched_stocks")
    if not stocks:
        return {"error": "enriched_stocks 누락"}

    try:
        themes = cluster_by_sector(stocks)
        logger.info(f"  생성된 테마: {len(themes)}개")

        selected = select_top_themes(themes, target=THEME_TARGET)
        logger.info(f"  선택된 테마: {len(selected)}개")

        return {
            "theme_clusters": themes,
            "selected_themes": selected,
            "metrics": _update_metrics(state, "cluster_themes", time.time() - node_start),
        }
    except Exception as e:
        logger.error(f"  테마 클러스터링 실패: {e}")
        return {
            "error": f"Theme clustering failed: {e}",
            "metrics": _update_metrics(state, "cluster_themes", time.time() - node_start, "failed"),
        }


def _call_perplexity(client, query):
    """Perplexity API 호출 (timeout + retry 적용)."""

    def _do_call():
        return client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": query}],
            web_search_options={"search_domain_filter": KOREAN_FINANCIAL_DOMAINS},
            timeout=API_TIMEOUT,
        )

    return retry_with_backoff(_do_call)()


@traceable(name="search_catalysts_perplexity", run_type="llm")
def search_catalysts_perplexity_node(state: KeywordPipelineState) -> dict:
    """Phase 3: Perplexity로 테마별 카탈리스트 뉴스 검색."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] search_catalysts_perplexity")

    perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not perplexity_key:
        logger.warning("  PERPLEXITY_API_KEY 없음, 카탈리스트 스킵")
        return {"stock_news_map": {}, "news_articles": []}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")
        themes = state.get("selected_themes", [])
        stocks = state.get("enriched_stocks") or []

        stock_news_map = {}
        all_articles = []

        for theme in themes:
            theme_stocks = theme.get("stocks", [])
            stock_names = [s.get("stock_name", s.get("stock_code", "")) for s in theme_stocks]
            sector = theme.get("sector", "")
            if not stock_names:
                continue

            query = (
                f"한국 주식시장 {sector} 섹터 최근 1주일 주요 뉴스를 알려줘. "
                f"관련 종목: {', '.join(stock_names[:5])}. "
                f"각 종목별로 주가에 영향을 준 핵심 뉴스 1개씩만 제목과 출처를 알려줘. "
                f'JSON 형식: [{{"stock_name": "...", "title": "뉴스 제목", "source": "출처명"}}]'
            )

            try:
                response = _call_perplexity(client, query)

                content = response.choices[0].message.content
                citations = getattr(response, "citations", []) or []

                # JSON 파싱 + 필드 검증
                json_match = re.search(r"\[.*?\]", content, re.DOTALL)
                news_items = []
                if json_match:
                    try:
                        raw_items = json.loads(json_match.group())
                        for item in raw_items:
                            if isinstance(item, dict) and "stock_name" in item and "title" in item:
                                news_items.append(item)
                            else:
                                logger.warning(f"  뉴스 항목 검증 실패: {item}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"  JSON 파싱 실패: {e}")

                # 종목코드에 매핑
                name_to_code = {s.get("stock_name", ""): s["stock_code"] for s in stocks if "stock_code" in s}
                for item in news_items:
                    sname = item.get("stock_name", "")
                    if sname in name_to_code:
                        code = name_to_code[sname]
                        catalyst = {
                            "title": item.get("title", ""),
                            "url": citations[0] if citations else "",
                            "source": item.get("source", "Perplexity"),
                            "published_at": datetime.now(timezone.utc).isoformat(),
                            "citations": citations,
                        }
                        stock_news_map[code] = catalyst
                        all_articles.append({**catalyst, "stock_code": code, "stock_name": sname})

                # JSON 파싱 실패 시 전체 텍스트를 카탈리스트로 사용
                if not news_items and content.strip():
                    for sname in stock_names[:3]:
                        if sname in name_to_code:
                            code = name_to_code[sname]
                            if code not in stock_news_map:
                                catalyst = {
                                    "title": content[:200].strip(),
                                    "url": citations[0] if citations else "",
                                    "source": "Perplexity",
                                    "published_at": datetime.now(timezone.utc).isoformat(),
                                    "citations": citations,
                                }
                                stock_news_map[code] = catalyst
                                all_articles.append({**catalyst, "stock_code": code, "stock_name": sname})

            except Exception as e:
                logger.warning(f"  테마 '{sector}' Perplexity 검색 실패: {e}")
                continue

        matched = len(stock_news_map)
        total = len(stocks)
        rate = (matched / total * 100) if total > 0 else 0
        logger.info(f"  Perplexity 카탈리스트 매칭: {matched}/{total}개 ({rate:.0f}%)")
        logger.info(f"  citations 수집: {sum(len(a.get('citations', [])) for a in all_articles)}개")

        return {
            "stock_news_map": stock_news_map,
            "news_articles": all_articles,
            "metrics": _update_metrics(state, "search_catalysts", time.time() - node_start),
        }

    except Exception as e:
        logger.warning(f"  Perplexity 검색 실패 (계속 진행): {e}")
        return {
            "stock_news_map": {},
            "news_articles": [],
            "metrics": _update_metrics(state, "search_catalysts", time.time() - node_start, "failed"),
        }


@traceable(name="research_sector_deep_dive", run_type="llm")
def research_sector_deep_dive_node(state: KeywordPipelineState) -> dict:
    """Phase 3-2: Perplexity 섹터별 심층 분석."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] research_sector_deep_dive")

    perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not perplexity_key:
        logger.warning("  PERPLEXITY_API_KEY 없음, 섹터 분석 스킵")
        return {"sector_analyses": {}}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")
        themes = state.get("selected_themes", [])
        sector_analyses = {}
        analyzed_sectors = set()

        for theme in themes:
            sector = theme.get("sector", "")
            if not sector or sector in analyzed_sectors or sector == "기타":
                continue
            analyzed_sectors.add(sector)

            query = (
                f"한국 주식시장 {sector} 섹터 심층 분석:\n"
                f"1. 주요 공급망 구조 (upstream/downstream 핵심 기업)\n"
                f"2. 주요 경쟁사 및 최근 시장 점유율 변화\n"
                f"3. 최근 규제 변화 및 정책 동향\n"
                f"4. 향후 3-6개월 전망\n"
                f"간결하게 각 항목별 2-3문장으로 요약해줘."
            )

            try:
                response = _call_perplexity(client, query)
                sector_analyses[sector] = {
                    "analysis": response.choices[0].message.content,
                    "citations": getattr(response, "citations", []) or [],
                }
                logger.info(f"  섹터 '{sector}' 분석 완료 (citations: {len(sector_analyses[sector]['citations'])}개)")
            except Exception as e:
                logger.warning(f"  섹터 '{sector}' 분석 실패: {e}")
                continue

        logger.info(f"  총 {len(sector_analyses)}개 섹터 분석 완료")
        return {
            "sector_analyses": sector_analyses,
            "metrics": _update_metrics(state, "research_sector", time.time() - node_start),
        }

    except Exception as e:
        logger.warning(f"  섹터 분석 실패 (계속 진행): {e}")
        return {
            "sector_analyses": {},
            "metrics": _update_metrics(state, "research_sector", time.time() - node_start, "failed"),
        }


@traceable(name="research_macro_environment", run_type="llm")
def research_macro_environment_node(state: KeywordPipelineState) -> dict:
    """Phase 3-3: Perplexity 거시경제 환경 분석."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] research_macro_environment")

    perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not perplexity_key:
        logger.warning("  PERPLEXITY_API_KEY 없음, 매크로 분석 스킵")
        return {"macro_context": {}}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")

        query = (
            "한국 주식시장 거시경제 환경 분석:\n"
            "1. 한국은행 기준금리 현황 및 향후 3개월 전망\n"
            "2. 원/달러 환율 동향 및 주요 영향 요인\n"
            "3. 반도체/배터리 등 주력 산업 경기 사이클 단계\n"
            "4. 외국인/기관 투자자 동향 (최근 1개월)\n"
            "간결하게 각 항목별 2-3문장으로 요약해줘."
        )

        response = _call_perplexity(client, query)

        citations = getattr(response, "citations", []) or []
        macro_context = {
            "analysis": response.choices[0].message.content,
            "citations": citations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"  매크로 분석 완료 (citations: {len(citations)}개, {len(macro_context['analysis'])}자)")
        return {
            "macro_context": macro_context,
            "metrics": _update_metrics(state, "research_macro", time.time() - node_start),
        }

    except Exception as e:
        logger.warning(f"  매크로 분석 실패 (계속 진행): {e}")
        return {
            "macro_context": {},
            "metrics": _update_metrics(state, "research_macro", time.time() - node_start, "failed"),
        }


@traceable(name="generate_keywords", run_type="llm")
def generate_keywords_node(state: KeywordPipelineState) -> dict:
    """Phase 4-1: LLM 키워드 생성."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] generate_keywords")

    try:
        from scripts.seed_fresh_data_integrated import generate_keyword_llm

        themes = state.get("selected_themes")
        api_key = state.get("openai_api_key")
        if not themes or not api_key:
            return {"error": "selected_themes 또는 openai_api_key 누락"}

        sector_analyses = state.get("sector_analyses") or {}
        macro_context = state.get("macro_context") or {}
        keywords = []

        for theme in themes:
            try:
                # 섹터 분석 결과를 테마에 주입
                sector = theme.get("sector", "")
                if sector in sector_analyses:
                    theme["sector_analysis"] = sector_analyses[sector].get("analysis", "")[:ANALYSIS_TRUNCATION]
                if macro_context.get("analysis"):
                    theme["macro_context"] = macro_context["analysis"][:ANALYSIS_TRUNCATION]

                kw = generate_keyword_llm(theme, api_key)
                kw["quality_score"] = calculate_quality_score(kw)

                # 섹터 분석 존재 시 품질 점수 보너스
                if sector in sector_analyses:
                    kw["quality_score"] = min(100, kw["quality_score"] + SECTOR_ANALYSIS_BONUS)
                # 매크로 컨텍스트 존재 시 추가 보너스
                if macro_context.get("analysis"):
                    kw["quality_score"] = min(100, kw["quality_score"] + MACRO_CONTEXT_BONUS)

                keywords.append(kw)
            except Exception as e:
                logger.warning(f"  테마 키워드 생성 실패: {e}")

        logger.info(f"  키워드 생성: {len(keywords)}개")

        if not keywords:
            return {
                "error": "No keywords generated",
                "metrics": _update_metrics(state, "generate_keywords", time.time() - node_start, "failed"),
            }

        return {
            "keyword_candidates": keywords,
            "metrics": _update_metrics(state, "generate_keywords", time.time() - node_start),
        }
    except Exception as e:
        logger.error(f"  키워드 생성 실패: {e}")
        return {
            "error": f"Keyword generation failed: {e}",
            "metrics": _update_metrics(state, "generate_keywords", time.time() - node_start, "failed"),
        }


@traceable(name="select_final_keywords", run_type="tool")
def select_final_keywords_node(state: KeywordPipelineState) -> dict:
    """Phase 4-2: 품질 점수 기반 최종 키워드 선택."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] select_final_keywords")

    try:
        candidates = state.get("keyword_candidates")
        stocks = state.get("enriched_stocks")
        if not candidates:
            return {"error": "keyword_candidates 누락"}
        if not stocks:
            return {"error": "enriched_stocks 누락"}

        # Sector Rotation 점수 조정 (macro_context 활용)
        macro_context = state.get("macro_context") or {}
        if macro_context.get("analysis"):
            cycle = determine_economic_cycle(macro_context)
            logger.info(f"  경기 사이클: {cycle}")
            favored = SECTOR_ROTATION_MAP.get(cycle, [])
            for kw in candidates:
                sector = kw.get("sector", "")
                if any(f in sector for f in favored):
                    kw["quality_score"] = min(100, kw["quality_score"] + SECTOR_ROTATION_BONUS)
                    logger.info(f"    ↑ {kw['title']}: +{SECTOR_ROTATION_BONUS}점 (섹터 로테이션 {cycle})")

        # 상승/하락 다양성을 고려한 선택
        RISING_TYPES = {"consecutive_rise", "majority_rise", "volume_surge"}
        FALLING_TYPES = {"consecutive_fall", "majority_fall"}

        rising = sorted(
            [k for k in candidates if k.get("trend_type", "") in RISING_TYPES],
            key=lambda k: k["quality_score"], reverse=True,
        )
        falling = sorted(
            [k for k in candidates if k.get("trend_type", "") in FALLING_TYPES],
            key=lambda k: k["quality_score"], reverse=True,
        )

        if len(rising) >= 2 and len(falling) >= 1:
            final = rising[:2] + falling[:1]
        elif len(falling) >= 1:
            final = falling[:1]
            remaining = sorted(
                [k for k in candidates if k not in final],
                key=lambda k: k["quality_score"], reverse=True,
            )
            final += remaining[:FINAL_KEYWORDS - len(final)]
        else:
            sorted_kw = sorted(candidates, key=lambda k: k["quality_score"], reverse=True)
            final = sorted_kw[:FINAL_KEYWORDS]

        final.sort(key=lambda k: k["quality_score"], reverse=True)
        logger.info(f"  다양성: 상승 {sum(1 for k in final if k.get('trend_type','') in RISING_TYPES)}개, "
                    f"하락 {sum(1 for k in final if k.get('trend_type','') in FALLING_TYPES)}개")

        # 최소 FINAL_KEYWORDS개 보장 (fallback)
        if len(final) < FINAL_KEYWORDS:
            logger.warning(f"  키워드 {len(final)}개만 생성, 템플릿 추가")
            for stock in sorted(stocks, key=lambda s: s.get("volume", 0), reverse=True):
                if len(final) >= FINAL_KEYWORDS:
                    break
                fallback_kw = {
                    "title": f"{stock.get('stock_name', stock['stock_code'])} 거래량 급증",
                    "description": f"{stock.get('trend_days', 0)}일 트렌드, {stock.get('change_rate', 0):+.1f}%",
                    "sector": stock.get("sector", "기타"),
                    "stocks": [stock["stock_code"]],
                    "trend_days": stock.get("trend_days", 0),
                    "trend_type": stock.get("trend_type", ""),
                    "mirroring_hint": "",
                    "quality_score": FALLBACK_QUALITY_SCORE,
                }
                final.append(fallback_kw)

        logger.info(f"  최종 선택: {len(final)}개 키워드")
        avg_score = sum(k["quality_score"] for k in final) / len(final)
        logger.info(f"  평균 품질 점수: {avg_score:.1f}/100")

        return {
            "final_keywords": final,
            "metrics": _update_metrics(state, "select_final_keywords", time.time() - node_start),
        }
    except Exception as e:
        logger.error(f"  최종 선택 실패: {e}")
        return {
            "error": f"Final selection failed: {e}",
            "metrics": _update_metrics(state, "select_final_keywords", time.time() - node_start, "failed"),
        }


@traceable(name="save_to_database", run_type="tool")
def save_to_db_node(state: KeywordPipelineState) -> dict:
    """DB 저장."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] save_to_database")

    try:
        import asyncio

        from scripts.seed_fresh_data_integrated import save_to_db

        end_date_obj = state.get("end_date_obj")
        stocks = state.get("enriched_stocks")
        keywords = state.get("final_keywords")
        if not end_date_obj or not stocks or not keywords:
            return {"error": "save_to_db에 필요한 state 키 누락 (end_date_obj, enriched_stocks, final_keywords)"}

        date = end_date_obj.date()
        news_map = state.get("stock_news_map") or {}

        asyncio.run(save_to_db(date, stocks, news_map, keywords))
        logger.info("  DB 저장 완료")

        metrics = _update_metrics(state, "save_to_database", time.time() - node_start)
        metrics["db_saved"] = True
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"  DB 저장 실패: {e}")
        return {
            "error": f"DB save failed: {e}",
            "metrics": _update_metrics(state, "save_to_database", time.time() - node_start, "failed"),
        }


# ============================================================
# 조건부 라우팅
# ============================================================


def check_error(state: KeywordPipelineState) -> str:
    """에러 발생 시 END로, 아니면 continue."""
    if state.get("error"):
        logger.error(f"파이프라인 중단: {state['error']}")
        return "error"
    return "continue"


# ============================================================
# Graph 빌드
# ============================================================


def build_keyword_pipeline() -> StateGraph:
    """키워드 생성 파이프라인 그래프 빌드."""
    graph = StateGraph(KeywordPipelineState)

    # 노드 추가
    graph.add_node("collect_market_data", collect_market_data_node)
    graph.add_node("filter_trends", filter_trends_node)
    graph.add_node("enrich_sectors", enrich_sectors_node)
    graph.add_node("cluster_themes", cluster_themes_node)
    graph.add_node("search_catalysts", search_catalysts_perplexity_node)
    graph.add_node("research_sector", research_sector_deep_dive_node)
    graph.add_node("research_macro", research_macro_environment_node)
    graph.add_node("generate_keywords", generate_keywords_node)
    graph.add_node("select_final_keywords", select_final_keywords_node)
    graph.add_node("save_to_database", save_to_db_node)

    # 엣지 추가
    graph.add_edge(START, "collect_market_data")

    graph.add_conditional_edges(
        "collect_market_data",
        check_error,
        {"error": END, "continue": "filter_trends"},
    )

    graph.add_conditional_edges(
        "filter_trends", check_error, {"error": END, "continue": "enrich_sectors"}
    )

    graph.add_edge("enrich_sectors", "cluster_themes")

    graph.add_conditional_edges(
        "cluster_themes", check_error, {"error": END, "continue": "search_catalysts"}
    )

    # search_catalysts → 병렬: research_sector, research_macro
    # 합류 후 generate_keywords
    graph.add_edge("search_catalysts", "research_sector")
    graph.add_edge("search_catalysts", "research_macro")
    graph.add_edge("research_sector", "generate_keywords")
    graph.add_edge("research_macro", "generate_keywords")

    graph.add_conditional_edges(
        "generate_keywords",
        check_error,
        {"error": END, "continue": "select_final_keywords"},
    )

    graph.add_edge("select_final_keywords", "save_to_database")
    graph.add_edge("save_to_database", END)

    return graph.compile()


# ============================================================
# 메인 실행
# ============================================================


@traceable(name="keyword_pipeline_full", run_type="chain")
def run_keyword_pipeline():
    """LangGraph 키워드 파이프라인 실행."""
    logger.info("=" * 70)
    logger.info("LangGraph 키워드 파이프라인 시작")
    logger.info("=" * 70)

    # 환경변수 사전 검증
    required_vars = ["OPENAI_API_KEY", "DATABASE_URL"]
    optional_vars = ["PERPLEXITY_API_KEY", "LANGCHAIN_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"필수 환경변수 누락: {', '.join(missing)}")
        return False
    for v in optional_vars:
        if not os.getenv(v):
            logger.warning(f"선택 환경변수 미설정: {v}")

    openai_key = os.getenv("OPENAI_API_KEY")

    # 초기 상태
    initial_state = KeywordPipelineState(
        end_date_str=None,
        end_date_obj=None,
        raw_market_data=None,
        trending_stocks=None,
        enriched_stocks=None,
        theme_clusters=None,
        selected_themes=None,
        news_articles=None,
        stock_news_map=None,
        sector_analyses=None,
        macro_context=None,
        keyword_candidates=None,
        final_keywords=None,
        openai_api_key=openai_key,
        error=None,
        metrics={},
    )

    # 그래프 빌드 및 실행
    pipeline = build_keyword_pipeline()

    try:
        start_time = datetime.now()
        result = pipeline.invoke(initial_state)
        elapsed = (datetime.now() - start_time).total_seconds()

        if result.get("error"):
            logger.error(f"파이프라인 실패: {result['error']}")
            return False

        # 결과 요약
        logger.info("=" * 70)
        logger.info("LangGraph 파이프라인 완료!")
        logger.info("=" * 70)

        final_kws = result.get("final_keywords", [])
        logger.info(f"최종 키워드: {len(final_kws)}개")
        if final_kws:
            avg = sum(k["quality_score"] for k in final_kws) / len(final_kws)
            logger.info(f"평균 품질 점수: {avg:.1f}/100")
        logger.info(f"트렌딩 종목: {len(result.get('enriched_stocks', []))}개")
        logger.info(f"뉴스 매칭: {len(result.get('stock_news_map', {}))}개")
        logger.info(f"총 실행 시간: {elapsed:.1f}초")

        # 노드별 메트릭 출력
        metrics = result.get("metrics", {})
        if metrics:
            logger.info("── 노드별 실행 시간 ──")
            for node_name, info in sorted(metrics.items()):
                if isinstance(info, dict) and "elapsed_s" in info:
                    logger.info(f"  {node_name}: {info['elapsed_s']}s ({info.get('status', 'ok')})")

        return True

    except Exception as e:
        logger.error(f"파이프라인 실행 오류: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_keyword_pipeline()
    sys.exit(0 if success else 1)
