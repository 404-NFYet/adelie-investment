"""LangGraph 기반 키워드 생성 파이프라인.

순차 실행 스크립트를 LangGraph 노드 기반으로 재구성하여
- 각 단계별 실행 시간 추적
- LangSmith 자동 트래킹
- 에러 핸들링 및 재시도
- 모니터링 지표 수집
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TypedDict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

# 한국 금융 뉴스 도메인 필터 (Perplexity search_domain_filter)
KOREAN_FINANCIAL_DOMAINS = [
    "naver.com",
    "hankyung.com",
    "chosun.com",
    "mk.co.kr",
    "sedaily.com",
    "bloter.net",
    "etnews.com",
    "thebell.co.kr",
]

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 기존 함수들 임포트
from scripts.seed_fresh_data_integrated import (
    calculate_quality_score,
    calculate_technical_indicators,
    calculate_trend_metrics,
    cluster_by_sector,
    fetch_multi_day_data,
    get_latest_trading_date,
    select_top_themes,
    select_top_trending,
)


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
    metrics: dict  # 실행 시간, 토큰 사용량 등


# ============================================================
# Node 함수들
# ============================================================


@traceable(name="collect_market_data", run_type="tool")
def collect_market_data_node(state: KeywordPipelineState) -> dict:
    """Phase 1-1: pykrx로 5일 시장 데이터 수집."""
    print("\n[Node] collect_market_data")

    if state.get("error"):
        return {}

    try:
        end_date_str, end_date_obj = get_latest_trading_date()
        print(f"  최근 영업일: {end_date_str}")

        df_all = fetch_multi_day_data(end_date_str, days=5)
        # DataFrame을 그대로 전달 (index 구조 유지 필요)
        print(f"  5일 데이터 수집: {len(df_all)}건")

        return {
            "end_date_str": end_date_str,
            "end_date_obj": end_date_obj,
            "raw_market_data": df_all,  # DataFrame 그대로
        }
    except Exception as e:
        print(f"  ❌ 시장 데이터 수집 실패: {e}")
        return {"error": f"Market data collection failed: {e}"}


@traceable(name="filter_trends", run_type="tool")
def filter_trends_node(state: KeywordPipelineState) -> dict:
    """Phase 1-2: 멀티데이 트렌드 필터링."""
    print("\n[Node] filter_trends")

    if state.get("error"):
        return {}

    try:
        # raw_market_data는 이미 DataFrame
        df = state["raw_market_data"]
        end_date_str = state["end_date_str"]

        trending = calculate_trend_metrics(df)
        print(f"  트렌드 감지: {len(trending)}개 종목")

        if len(trending) < 5:
            return {"error": f"Too few trending stocks: {len(trending)}"}

        # RSI/MACD 기술 지표 계산 (상위 후보 종목만)
        top_codes = [s["stock_code"] for s in sorted(trending, key=lambda x: abs(x["change_rate"]), reverse=True)[:30]]
        indicators = {}
        try:
            indicators = calculate_technical_indicators(top_codes, end_date_str)
            print(f"  기술 지표 계산: {len(indicators)}개 종목 (RSI/MACD)")
        except Exception as e:
            print(f"  ⚠️  기술 지표 계산 실패 (계속 진행): {e}")

        selected = select_top_trending(trending, target=15, indicators=indicators)
        print(f"  상위 {len(selected)}개 선택")

        # 종목명 추가
        from pykrx import stock as pykrx_stock

        for s in selected:
            try:
                s["stock_name"] = pykrx_stock.get_market_ticker_name(s["stock_code"])
            except:
                s["stock_name"] = s["stock_code"]

        return {"trending_stocks": selected}
    except Exception as e:
        print(f"  ❌ 트렌드 필터링 실패: {e}")
        return {"error": f"Trend filtering failed: {e}"}


@traceable(name="enrich_sectors", run_type="tool")
def enrich_sectors_node(state: KeywordPipelineState) -> dict:
    """Phase 2-1: 섹터 정보 enrichment."""
    print("\n[Node] enrich_sectors")

    if state.get("error"):
        return {}

    try:
        import asyncio

        from scripts.seed_fresh_data_integrated import enrich_with_sectors

        stocks = state["trending_stocks"]
        enriched = asyncio.run(enrich_with_sectors(stocks))
        print(f"  섹터 정보 매핑: {len(enriched)}개")

        return {"enriched_stocks": enriched}
    except Exception as e:
        print(f"  ⚠️  섹터 매핑 실패 (계속 진행): {e}")
        # 섹터 정보 없어도 계속 진행
        return {"enriched_stocks": state["trending_stocks"]}


@traceable(name="cluster_themes", run_type="tool")
def cluster_themes_node(state: KeywordPipelineState) -> dict:
    """Phase 2-2: 섹터별 테마 클러스터링."""
    print("\n[Node] cluster_themes")

    if state.get("error"):
        return {}

    try:
        stocks = state["enriched_stocks"]
        themes = cluster_by_sector(stocks)
        print(f"  생성된 테마: {len(themes)}개")

        selected = select_top_themes(themes, target=5)
        print(f"  선택된 테마: {len(selected)}개")

        return {"theme_clusters": themes, "selected_themes": selected}
    except Exception as e:
        print(f"  ❌ 테마 클러스터링 실패: {e}")
        return {"error": f"Theme clustering failed: {e}"}


@traceable(name="search_catalysts_perplexity", run_type="llm")
def search_catalysts_perplexity_node(state: KeywordPipelineState) -> dict:
    """Phase 3: Perplexity로 테마별 카탈리스트 뉴스 검색.

    - sonar-pro 모델 사용 (더 많은 citations, 200K context)
    - search_domain_filter로 한국 금융 뉴스 도메인만 검색
    - citations를 각 article에 저장
    """
    print("\n[Node] search_catalysts_perplexity")

    if state.get("error"):
        return {}

    perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not perplexity_key:
        print("  ⚠️  PERPLEXITY_API_KEY 없음, 카탈리스트 스킵")
        return {"stock_news_map": {}, "news_articles": []}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")
        themes = state.get("selected_themes", [])
        stocks = state["enriched_stocks"]

        stock_news_map = {}  # stock_code → {title, url, source, published_at, citations}
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
                f"JSON 형식: [{{\"stock_name\": \"...\", \"title\": \"뉴스 제목\", \"source\": \"출처명\"}}]"
            )

            try:
                response = client.chat.completions.create(
                    model="sonar-pro",
                    messages=[{"role": "user", "content": query}],
                    search_domain_filter=KOREAN_FINANCIAL_DOMAINS,
                )

                content = response.choices[0].message.content
                citations = getattr(response, "citations", []) or []

                # JSON 파싱 시도
                import re
                json_match = re.search(r'\[.*?\]', content, re.DOTALL)
                if json_match:
                    try:
                        news_items = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        news_items = []
                else:
                    news_items = []

                # 종목코드에 매핑
                name_to_code = {s["stock_name"]: s["stock_code"] for s in stocks}
                for item in news_items:
                    sname = item.get("stock_name", "")
                    if sname in name_to_code:
                        code = name_to_code[sname]
                        catalyst = {
                            "title": item.get("title", ""),
                            "url": citations[0] if citations else "",
                            "source": item.get("source", "Perplexity"),
                            "published_at": datetime.now(timezone.utc).isoformat(),
                            "citations": citations,  # 전체 citations 저장
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
                print(f"  ⚠️  테마 '{sector}' Perplexity 검색 실패: {e}")
                continue

        matched = len(stock_news_map)
        total = len(stocks)
        rate = (matched / total * 100) if total > 0 else 0
        print(f"  Perplexity 카탈리스트 매칭: {matched}/{total}개 ({rate:.0f}%)")
        print(f"  citations 수집: {sum(len(a.get('citations', [])) for a in all_articles)}개")

        return {"stock_news_map": stock_news_map, "news_articles": all_articles}

    except Exception as e:
        print(f"  ⚠️  Perplexity 검색 실패 (계속 진행): {e}")
        return {"stock_news_map": {}, "news_articles": []}


@traceable(name="research_sector_deep_dive", run_type="llm")
def research_sector_deep_dive_node(state: KeywordPipelineState) -> dict:
    """Phase 3-2: Perplexity 섹터별 심층 분석.

    각 선택된 테마의 섹터에 대해 공급망, 경쟁 구도, 규제 동향을 분석한다.
    """
    print("\n[Node] research_sector_deep_dive")

    if state.get("error"):
        return {}

    perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not perplexity_key:
        print("  ⚠️  PERPLEXITY_API_KEY 없음, 섹터 분석 스킵")
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
                response = client.chat.completions.create(
                    model="sonar-pro",
                    messages=[{"role": "user", "content": query}],
                    search_domain_filter=KOREAN_FINANCIAL_DOMAINS,
                )

                sector_analyses[sector] = {
                    "analysis": response.choices[0].message.content,
                    "citations": getattr(response, "citations", []) or [],
                }
                print(f"  섹터 '{sector}' 분석 완료 (citations: {len(sector_analyses[sector]['citations'])}개)")
            except Exception as e:
                print(f"  ⚠️  섹터 '{sector}' 분석 실패: {e}")
                continue

        print(f"  총 {len(sector_analyses)}개 섹터 분석 완료")
        return {"sector_analyses": sector_analyses}

    except Exception as e:
        print(f"  ⚠️  섹터 분석 실패 (계속 진행): {e}")
        return {"sector_analyses": {}}


@traceable(name="research_macro_environment", run_type="llm")
def research_macro_environment_node(state: KeywordPipelineState) -> dict:
    """Phase 3-3: Perplexity 거시경제 환경 분석.

    기준금리, 환율, 산업 사이클, 투자자 동향을 분석하여
    키워드 품질 점수 조정 및 섹터 로테이션에 활용한다.
    """
    print("\n[Node] research_macro_environment")

    if state.get("error"):
        return {}

    perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not perplexity_key:
        print("  ⚠️  PERPLEXITY_API_KEY 없음, 매크로 분석 스킵")
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

        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": query}],
            search_domain_filter=KOREAN_FINANCIAL_DOMAINS,
        )

        citations = getattr(response, "citations", []) or []
        macro_context = {
            "analysis": response.choices[0].message.content,
            "citations": citations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        print(f"  매크로 분석 완료 (citations: {len(citations)}개)")
        print(f"  분석 길이: {len(macro_context['analysis'])}자")
        return {"macro_context": macro_context}

    except Exception as e:
        print(f"  ⚠️  매크로 분석 실패 (계속 진행): {e}")
        return {"macro_context": {}}


@traceable(name="generate_keywords", run_type="llm")
def generate_keywords_node(state: KeywordPipelineState) -> dict:
    """Phase 4-1: LLM 키워드 생성.

    sector_analyses와 macro_context를 활용하여 키워드 품질 향상.
    """
    print("\n[Node] generate_keywords")

    if state.get("error"):
        return {}

    try:
        from scripts.seed_fresh_data_integrated import generate_keyword_llm

        themes = state["selected_themes"]
        api_key = state["openai_api_key"]
        sector_analyses = state.get("sector_analyses") or {}
        macro_context = state.get("macro_context") or {}
        keywords = []

        for theme in themes:
            try:
                # 섹터 분석 결과를 테마에 주입
                sector = theme.get("sector", "")
                if sector in sector_analyses:
                    theme["sector_analysis"] = sector_analyses[sector].get("analysis", "")[:500]
                if macro_context.get("analysis"):
                    theme["macro_context"] = macro_context["analysis"][:500]

                kw = generate_keyword_llm(theme, api_key)
                kw["quality_score"] = calculate_quality_score(kw)

                # 섹터 분석 존재 시 품질 점수 보너스
                if sector in sector_analyses:
                    kw["quality_score"] = min(100, kw["quality_score"] + 5)
                # 매크로 컨텍스트 존재 시 추가 보너스
                if macro_context.get("analysis"):
                    kw["quality_score"] = min(100, kw["quality_score"] + 5)

                keywords.append(kw)
            except Exception as e:
                print(f"  ⚠️  테마 키워드 생성 실패: {e}")

        print(f"  키워드 생성: {len(keywords)}개")

        if not keywords:
            return {"error": "No keywords generated"}

        return {"keyword_candidates": keywords}
    except Exception as e:
        print(f"  ❌ 키워드 생성 실패: {e}")
        return {"error": f"Keyword generation failed: {e}"}


@traceable(name="select_final_keywords", run_type="tool")
def select_final_keywords_node(state: KeywordPipelineState) -> dict:
    """Phase 4-2: 품질 점수 기반 최종 키워드 선택."""
    print("\n[Node] select_final_keywords")

    if state.get("error"):
        return {}

    try:
        candidates = state["keyword_candidates"]
        stocks = state["enriched_stocks"]

        # 점수순 정렬
        sorted_kw = sorted(candidates, key=lambda k: k["quality_score"], reverse=True)
        final = sorted_kw[:3]

        # 최소 3개 보장 (fallback)
        if len(final) < 3:
            print(f"  ⚠️  키워드 {len(final)}개만 생성, 템플릿 추가")
            for stock in sorted(stocks, key=lambda s: s["volume"], reverse=True):
                if len(final) >= 3:
                    break
                fallback_kw = {
                    "title": f"{stock['stock_name']} 거래량 급증",
                    "description": f"{stock['trend_days']}일 트렌드, {stock['change_rate']:+.1f}%",
                    "sector": stock.get("sector", "기타"),
                    "stocks": [stock["stock_code"]],
                    "trend_days": stock["trend_days"],
                    "trend_type": stock["trend_type"],
                    "mirroring_hint": "",
                    "quality_score": 50,
                }
                final.append(fallback_kw)

        print(f"  최종 선택: {len(final)}개 키워드")
        avg_score = sum(k["quality_score"] for k in final) / len(final)
        print(f"  평균 품질 점수: {avg_score:.1f}/100")

        return {"final_keywords": final}
    except Exception as e:
        print(f"  ❌ 최종 선택 실패: {e}")
        return {"error": f"Final selection failed: {e}"}


@traceable(name="save_to_database", run_type="tool")
def save_to_db_node(state: KeywordPipelineState) -> dict:
    """DB 저장."""
    print("\n[Node] save_to_database")

    if state.get("error"):
        return {}

    try:
        import asyncio

        from scripts.seed_fresh_data_integrated import save_to_db

        date = state["end_date_obj"].date()
        stocks = state["enriched_stocks"]
        news_map = state.get("stock_news_map", {})
        keywords = state["final_keywords"]

        asyncio.run(save_to_db(date, stocks, news_map, keywords))
        print("  ✅ DB 저장 완료")

        return {"metrics": {**state.get("metrics", {}), "db_saved": True}}
    except Exception as e:
        print(f"  ❌ DB 저장 실패: {e}")
        return {"error": f"DB save failed: {e}"}


# ============================================================
# 조건부 라우팅
# ============================================================


def check_error(state: KeywordPipelineState) -> str:
    """에러 발생 시 END로, 아니면 continue."""
    if state.get("error"):
        print(f"\n❌ 파이프라인 중단: {state['error']}")
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

    # search_catalysts → 3개 병렬: research_sector, research_macro, generate_keywords 준비
    # sector/macro 분석은 병렬 실행 후 generate_keywords에서 합류
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
    print("=" * 70)
    print("🚀 LangGraph 키워드 파이프라인 시작")
    print("=" * 70)

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY 없음")
        return False

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
        end_time = datetime.now()

        elapsed = (end_time - start_time).total_seconds()
        print(f"\n⏱️  총 실행 시간: {elapsed:.1f}초")

        if result.get("error"):
            print(f"❌ 파이프라인 실패: {result['error']}")
            return False

        # 결과 요약
        print("\n" + "=" * 70)
        print("✅ LangGraph 파이프라인 완료!")
        print("=" * 70)
        print(f"최종 키워드: {len(result.get('final_keywords', []))}개")
        print(
            f"평균 품질 점수: {sum(k['quality_score'] for k in result.get('final_keywords', [])) / len(result.get('final_keywords', [])) if result.get('final_keywords') else 0:.1f}/100"
        )
        print(f"트렌딩 종목: {len(result.get('enriched_stocks', []))}개")
        print(f"뉴스 매칭: {len(result.get('stock_news_map', {}))}개")

        return True

    except Exception as e:
        print(f"\n❌ 파이프라인 실행 오류: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    success = run_keyword_pipeline()
    sys.exit(0 if success else 1)
