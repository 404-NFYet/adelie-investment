"""통합 데이터 파이프라인: Phase 1-4 연속 실행.

멀티데이 트렌드 감지 → 섹터 클러스터링 → RSS 뉴스 매칭 → 테마 키워드 생성을
하나의 파이프라인으로 실행하여 데이터 일관성 보장.

예외 처리:
- 휴일 자동 감지 및 fallback
- API 재시도 로직 (exponential backoff)
- 최소 데이터 보장 (키워드 3개, 종목 5개)
"""
import asyncio
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
import pandas as pd
from pykrx import stock as pykrx_stock

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


# ============================================================
# 재시도 데코레이터
# ============================================================

def retry_with_backoff(max_attempts=3, base_delay=2):
    """Exponential backoff 재시도 데코레이터."""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"  ❌ {func.__name__} 최종 실패: {e}")
                        raise
                    delay = base_delay * (2**attempt)
                    print(f"  ⚠️  {func.__name__} 실패 (시도 {attempt + 1}/{max_attempts}), {delay}초 후 재시도...")
                    await asyncio.sleep(delay)

        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"  ❌ {func.__name__} 최종 실패: {e}")
                        raise
                    delay = base_delay * (2**attempt)
                    print(f"  ⚠️  {func.__name__} 실패 (시도 {attempt + 1}/{max_attempts}), {delay}초 후 재시도...")
                    time.sleep(delay)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# ============================================================
# 상수 및 설정
# ============================================================

RSS_FEEDS = [
    "https://www.hankyung.com/feed/economy",
]

_SECTOR_MIRRORING_HINTS = {
    "반도체": "2018년 메모리 다운사이클: 삼성전자·SK하이닉스 주가 40%+ 하락 후 2019년 반등",
    "2차전지": "2021년 배터리주 급등락: LG에너지솔루션 IPO 전후 에코프로·엘앤에프 300%+ 상승 후 2022년 50% 조정",
    "자동차": "2020년 현대차 전기차 전략 발표: 주가 2배 상승 후 2021년 조정, 아이오닉5 출시 효과",
    "바이오": "2020년 셀트리온·삼성바이오로직스 코로나 수혜 급등, 2021년 임상 실패 리스크로 30% 조정",
    "건설": "2015년 해외건설 수주 급감: 대우건설·현대건설 주가 30% 하락, 부동산 PF 리스크 부각",
    "금융": "2008년 글로벌 금융위기: KB금융·신한지주 50% 급락 후 2009년 정부 지원으로 80% 반등",
    "IT 서비스": "2021년 카카오·네이버 플랫폼 확장: 카카오뱅크·카카오페이 상장, 주가 2배",
    "전기·전자": "2020년 삼성전자·LG전자 가전 호황: 재택근무 수요 급증, 주가 50% 상승",
    "기계·장비": "2021년 두산중공업·HD현대인프라코어 수주 증가: 풍력·건설기계 호황",
    "화학": "2021년 LG화학·SKC 배터리 소재 호황: 양극재·음극재 가격 2배, 에코프로비엠 급등",
}


# ============================================================
# RSSService (임베드)
# ============================================================

class RSSService:
    """RSS 피드 수집 서비스."""

    def __init__(self, feeds: list[str], timeout_seconds: int = 15):
        self.feeds = feeds
        self.timeout_seconds = timeout_seconds

    def fetch_top_news_structured(self, retry_48h: bool = False) -> list[dict]:
        """구조화된 뉴스 리스트 반환."""
        now = datetime.now(timezone.utc)
        window = timedelta(hours=48 if retry_48h else 24)
        cutoff = now - window
        news_items = []

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            for url in self.feeds:
                try:
                    response = client.get(url)
                    if response.status_code >= 400:
                        continue
                    xml = response.text
                    source = self._extract_source(url)
                    self._extract_items(xml, cutoff, news_items, source)
                except Exception:
                    pass

        if len(news_items) < 3 and not retry_48h:
            return self.fetch_top_news_structured(retry_48h=True)

        return news_items[:50]

    def _extract_items(self, xml: str, cutoff: datetime, collector: list, source: str):
        """RSS 아이템 추출."""
        pattern = re.compile(
            r"<item>[\s\S]*?<title>(.*?)</title>"
            r"[\s\S]*?<link>(.*?)</link>"
            r"(?:[\s\S]*?<description>(.*?)</description>)?"
            r"[\s\S]*?(?:<pubDate>(.*?)</pubDate>)?[\s\S]*?</item>",
            re.IGNORECASE,
        )

        for match in pattern.finditer(xml):
            if len(collector) >= 20:
                break
            title = self._clean(match.group(1))
            url = self._clean(match.group(2))
            desc = self._clean(match.group(3)) if match.group(3) else ""
            date_str = match.group(4)

            if not title or not url:
                continue
            if not self._is_recent(date_str, cutoff):
                continue

            collector.append({
                "title": title,
                "url": url,
                "description": desc[:200],
                "published_at": self._parse_date(date_str),
                "source": source,
            })

    @staticmethod
    def _clean(raw: str) -> str:
        """HTML 태그 제거."""
        text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", raw or "")
        text = re.sub(r"<[^>]*>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_source(url: str) -> str:
        """URL에서 출처 추출."""
        if "hankyung.com" in url:
            return "한국경제"
        return "기타"

    @staticmethod
    def _parse_date(date_str: str | None) -> str:
        """날짜 문자열을 ISO 형식으로 변환."""
        if not date_str:
            return datetime.now(timezone.utc).isoformat()
        try:
            dt = parsedate_to_datetime(date_str.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except:
            return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_recent(date_str: str | None, cutoff: datetime) -> bool:
        """최근 뉴스인지 확인."""
        if not date_str:
            return True
        try:
            dt = parsedate_to_datetime(date_str.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt >= cutoff
        except:
            return True


# ============================================================
# 기술적 지표 계산 (RSI, MACD) - pandas-ta 불필요
# ============================================================


def calculate_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """RSI (Relative Strength Index) 계산.

    RSI > 70: 과매수 (하락 리스크)
    RSI < 30: 과매도 (반등 기회)
    """
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return round(100 - (100 / (1 + rs)), 2)


def calculate_macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict | None:
    """MACD (Moving Average Convergence Divergence) 계산.

    MACD 골든크로스 (MACD > Signal): 상승 모멘텀
    MACD 데드크로스 (MACD < Signal): 하락 모멘텀
    """
    if len(closes) < slow + signal:
        return None
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(histogram.iloc[-1]), 4),
        "crossover": "bullish" if macd_line.iloc[-1] > signal_line.iloc[-1] else "bearish",
    }


def calculate_technical_indicators(stock_codes: list[str], end_date_str: str) -> dict:
    """선택된 종목들의 기술적 지표 계산.

    30일 OHLCV 데이터를 조회하여 RSI/MACD를 계산한다.
    """
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    start_date = (end_date - timedelta(days=45)).strftime("%Y%m%d")  # 충분한 기간
    results = {}

    for code in stock_codes:
        try:
            df = pykrx_stock.get_market_ohlcv_by_date(start_date, end_date_str, code)
            if df is None or len(df) < 14:
                continue

            closes = df["종가"]
            rsi = calculate_rsi(closes)
            macd = calculate_macd(closes)

            results[code] = {
                "rsi": rsi,
                "macd": macd,
                "macd_signal": macd["crossover"] if macd else None,
            }
        except Exception:
            continue

    return results


# ============================================================
# Sector Rotation 로직
# ============================================================

SECTOR_ROTATION_MAP = {
    "확장기": ["IT 서비스", "전기·전자", "소프트웨어", "반도체", "미디어·교육"],
    "정점": ["에너지", "화학", "철강·금속", "조선"],
    "수축기": ["음식료·담배", "의약품", "유틸리티", "통신"],
    "저점": ["금융", "부동산", "건설", "보험"],
}


def determine_economic_cycle(macro_context: dict) -> str:
    """거시경제 분석 결과로 경기 사이클 판단."""
    analysis = macro_context.get("analysis", "")
    if not analysis:
        return "확장기"  # 기본값

    # 키워드 기반 판단 (향후 LLM 활용 가능)
    tightening = sum(1 for kw in ["금리 인상", "긴축", "테이퍼링", "매파"] if kw in analysis)
    easing = sum(1 for kw in ["금리 인하", "완화", "비둘기", "양적완화"] if kw in analysis)
    growth = sum(1 for kw in ["확장", "성장", "호황", "수출 증가"] if kw in analysis)
    contraction = sum(1 for kw in ["수축", "둔화", "침체", "경기 후퇴"] if kw in analysis)

    if tightening > easing and growth > contraction:
        return "정점"
    elif easing > tightening:
        return "저점"
    elif growth > contraction:
        return "확장기"
    else:
        return "수축기"


def apply_sector_rotation_boost(stocks: list[dict], cycle_phase: str) -> list[dict]:
    """경기 사이클별 섹터 가중치 조정.

    유리한 섹터: 1.15배 가산
    불리한 섹터: 변동 없음 (1.0배)
    """
    favored_sectors = SECTOR_ROTATION_MAP.get(cycle_phase, [])

    for stock in stocks:
        sector = stock.get("sector", "")
        if any(fav in sector for fav in favored_sectors):
            stock["rotation_boost"] = 1.15
        else:
            stock["rotation_boost"] = 1.0

    return stocks


# ============================================================
# Phase 1: 멀티데이 트렌드 감지
# ============================================================

def get_latest_trading_date(max_days_back=7):
    """최근 영업일 반환."""
    today = datetime.now()
    for i in range(max_days_back):
        target = today - timedelta(days=i)
        date_str = target.strftime("%Y%m%d")
        try:
            tickers = pykrx_stock.get_market_ticker_list(date_str, market="KOSPI")
            if tickers and len(tickers) > 0:
                return date_str, target
        except:
            continue
    raise ValueError("최근 영업일 없음")


def fetch_multi_day_data(end_date_str, days=5):
    """N일 OHLCV 데이터 수집."""
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    df_list = []
    current = end_date
    collected = 0

    while collected < days and (end_date - current).days < days * 3:
        date_str = current.strftime("%Y%m%d")
        try:
            daily_df = pykrx_stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
            if daily_df is not None and len(daily_df) > 0:
                daily_df["date"] = date_str
                daily_df = daily_df[daily_df["거래량"] > 0]
                if len(daily_df) > 0:
                    df_list.append(daily_df)
                    collected += 1
        except:
            pass
        current -= timedelta(days=1)

    if not df_list:
        raise ValueError("데이터 수집 실패")

    return pd.concat(df_list)


def calculate_trend_metrics(df):
    """트렌드 메트릭 계산."""
    results = []
    for code in df.index.unique():
        stock_data = df.loc[[code]].sort_values("date")
        if len(stock_data) < 3:
            continue

        # 일별 변동률
        changes = []
        prev_close = None
        for _, row in stock_data.iterrows():
            if prev_close:
                change = ((row["종가"] - prev_close) / prev_close) * 100
                changes.append(change)
            prev_close = row["종가"]

        if len(changes) < 2:
            continue

        # 트렌드 감지
        consecutive_rise = all(c > 0 for c in changes[-3:]) if len(changes) >= 3 else False
        consecutive_fall = all(c < 0 for c in changes[-3:]) if len(changes) >= 3 else False

        recent_3 = changes[-3:] if len(changes) >= 3 else changes
        rise_count = sum(1 for c in recent_3 if c > 0)
        fall_count = sum(1 for c in recent_3 if c < 0)

        recent_volume = stock_data.iloc[-1]["거래량"]
        avg_volume = stock_data["거래량"].mean()
        volume_surge = (recent_volume / avg_volume) >= 1.5 if avg_volume > 0 else False

        # 트렌드 타입 결정
        trend_type = None
        trend_days = 0
        tier = None

        if consecutive_rise:
            trend_type, trend_days, tier = "consecutive_rise", len(changes), 1
        elif consecutive_fall:
            trend_type, trend_days, tier = "consecutive_fall", len(changes), 1
        elif rise_count >= 2:
            trend_type, trend_days, tier = "majority_rise", rise_count, 2
        elif fall_count >= 2:
            trend_type, trend_days, tier = "majority_fall", fall_count, 2
        elif volume_surge:
            trend_type, trend_days, tier = "volume_surge", 1, 3

        if trend_type:
            latest = stock_data.iloc[-1]
            results.append({
                "stock_code": code,
                "trend_type": trend_type,
                "trend_days": trend_days,
                "tier": tier,
                "close": int(latest["종가"]),
                "change_rate": round(changes[-1], 2),
                "volume": int(latest["거래량"]),
            })

    return results


def select_top_trending(trending_stocks, target=15, indicators=None, macro_context=None):
    """상위 trending stocks 선택.

    기술 지표 + 섹터 로테이션 고려 종합 점수 기반 선정.
    indicators: {stock_code: {rsi, macd, macd_signal}} (optional)
    macro_context: {analysis, citations} (optional)
    """
    indicators = indicators or {}
    filtered = []

    # Phase 1: RSI 필터링 (과매수 극단 제외)
    for s in trending_stocks:
        code = s["stock_code"]
        ind = indicators.get(code, {})
        rsi = ind.get("rsi")

        # RSI 80 이상 (과매수 극단) 제외, 상승 트렌드인 경우만
        if rsi is not None and rsi > 80 and s.get("trend_type", "").endswith("rise"):
            continue
        # RSI 정보를 종목에 추가
        if rsi is not None:
            s["rsi"] = rsi
        if ind.get("macd_signal"):
            s["macd_signal"] = ind["macd_signal"]
        filtered.append(s)

    rsi_filtered = len(trending_stocks) - len(filtered)
    if rsi_filtered > 0:
        print(f"  RSI 필터링: {rsi_filtered}개 과매수 종목 제외")

    # Phase 2: 경기 사이클별 섹터 가중치
    if macro_context and macro_context.get("analysis"):
        cycle = determine_economic_cycle(macro_context)
        filtered = apply_sector_rotation_boost(filtered, cycle)
        print(f"  경기 사이클 판단: {cycle}")
    else:
        for s in filtered:
            s["rotation_boost"] = 1.0

    # Phase 3: 종합 점수 계산
    for s in filtered:
        base_score = (4 - s["tier"]) * 10  # Tier 1=30, Tier 2=20, Tier 3=10
        base_score += min(10, abs(s["change_rate"]))  # 변동률 보너스 (최대 10)

        # MACD 골든크로스 보너스
        if s.get("macd_signal") == "bullish":
            base_score += 5

        # Rotation 가중치
        base_score *= s.get("rotation_boost", 1.0)

        s["selection_score"] = round(base_score, 2)

    # 점수 기반 정렬 및 선택
    sorted_stocks = sorted(filtered, key=lambda x: x.get("selection_score", 0), reverse=True)
    return sorted_stocks[:target]


# ============================================================
# Phase 2: 섹터 클러스터링
# ============================================================

async def enrich_with_sectors(stocks):
    """stock_listings에서 섹터 정보 조회."""
    from app.core.database import AsyncSessionLocal
    from app.models.stock_listing import StockListing
    from sqlalchemy import select

    codes = [s["stock_code"] for s in stocks]

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(StockListing).where(StockListing.stock_code.in_(codes)))
        listings = result.scalars().all()
        sector_map = {l.stock_code: l.sector for l in listings}

    for stock in stocks:
        stock["sector"] = sector_map.get(stock["stock_code"], "기타")

    return stocks


def cluster_by_sector(stocks):
    """섹터별 클러스터링."""
    sector_groups = defaultdict(list)
    for s in stocks:
        sector_groups[s.get("sector", "기타")].append(s)

    themes = []
    trend_map = {
        "consecutive_rise": "연속 상승",
        "consecutive_fall": "연속 하락",
        "majority_rise": "상승 우세",
        "majority_fall": "하락 우세",
        "volume_surge": "거래량 급증",
    }

    for sector, sector_stocks in sector_groups.items():
        trend_groups = defaultdict(list)
        for s in sector_stocks:
            trend_groups[s["trend_type"]].append(s)

        for trend_type, trend_stocks in trend_groups.items():
            if len(trend_stocks) >= 2:
                # 섹터 테마
                avg_change = sum(s["change_rate"] for s in trend_stocks) / len(trend_stocks)
                themes.append({
                    "type": "sector_theme",
                    "title": f"{sector} {trend_map.get(trend_type, '변동')} 신호",
                    "sector": sector,
                    "stocks": trend_stocks,
                    "avg_change_rate": avg_change,
                    "stock_count": len(trend_stocks),
                })
            else:
                # 개별 종목
                for s in trend_stocks:
                    themes.append({
                        "type": "individual_stock",
                        "title": f"{s.get('stock_name', s['stock_code'])} {trend_map.get(s['trend_type'], '변동')}",
                        "sector": sector,
                        "stocks": [s],
                        "avg_change_rate": s["change_rate"],
                        "stock_count": 1,
                    })

    return themes


def select_top_themes(themes, target=5):
    """다양성 고려 상위 테마 선택."""
    sector_themes = [t for t in themes if t["type"] == "sector_theme"]
    individual = [t for t in themes if t["type"] == "individual_stock"]

    selected = []
    used_sectors = set()

    # 섹터 테마 우선
    for t in sorted(sector_themes, key=lambda x: (x["stock_count"], abs(x["avg_change_rate"])), reverse=True):
        if t["sector"] not in used_sectors and len(selected) < target:
            selected.append(t)
            used_sectors.add(t["sector"])

    # 부족하면 개별 종목
    for t in sorted(individual, key=lambda x: abs(x["avg_change_rate"]), reverse=True):
        if len(selected) < target:
            selected.append(t)

    return selected[:target]


# ============================================================
# Phase 3: RSS 뉴스 매칭
# ============================================================

def preprocess_news(news_list):
    """뉴스 전처리: 중복 제거."""
    if not news_list:
        return []

    unique = []
    seen = []

    for news in news_list:
        title = news["title"]
        is_dup = False
        for seen_title in seen:
            if SequenceMatcher(None, title, seen_title).ratio() >= 0.9:
                is_dup = True
                break
        if not is_dup:
            unique.append(news)
            seen.append(title)

    unique.sort(key=lambda x: x["published_at"], reverse=True)
    return unique


@retry_with_backoff(max_attempts=3, base_delay=2)
def match_news_to_stocks_llm(stocks, news, api_key):
    """LLM 뉴스-종목 매칭 (재시도 포함)."""
    if not news or not stocks:
        return {}

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    stock_map = {s["stock_code"]: s.get("stock_name", s["stock_code"]) for s in stocks}
    result_map = {}

    # 배치 처리
    batch_size = 20
    for i in range(0, len(news), batch_size):
        batch = news[i : i + batch_size]
        news_str = "\n".join([f"{idx}. {n['title']}" for idx, n in enumerate(batch, 1)])
        stock_str = "\n".join([f"- {name} ({code})" for code, name in stock_map.items()])

        prompt = f"""다음 뉴스들이 어떤 종목에 관한 것인지 판단하세요.

뉴스:
{news_str}

후보 종목:
{stock_str}

응답 형식 (JSON):
{{"matches": [{{"news_index": 1, "stock_code": "005930"}}, {{"news_index": 2, "stock_code": "NONE"}}, ...]}}
"""

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            data = json.loads(resp.choices[0].message.content)

            for match in data.get("matches", []):
                idx = match.get("news_index", 0) - 1
                code = match.get("stock_code", "NONE")
                if 0 <= idx < len(batch) and code != "NONE" and code in stock_map:
                    if code not in result_map:
                        result_map[code] = {
                            "title": batch[idx]["title"],
                            "url": batch[idx]["url"],
                            "published_at": batch[idx]["published_at"],
                            "source": batch[idx]["source"],
                        }
        except Exception as e:
            print(f"  ⚠️  배치 {i // batch_size + 1} 매칭 실패: {e}")
            # 배치 실패는 전체 실패로 이어지지 않음

    return result_map


# ============================================================
# Phase 4: 테마 키워드 생성
# ============================================================

@retry_with_backoff(max_attempts=3, base_delay=2)
def generate_keyword_llm(theme, api_key):
    """LLM 키워드 생성 (재시도 포함)."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    sector = theme.get("sector", "기타")
    stocks = theme.get("stocks", [])
    avg_change = theme.get("avg_change_rate", 0)
    trend_type = stocks[0].get("trend_type", "") if stocks else ""
    trend_days = stocks[0].get("trend_days", 0) if stocks else 0

    hint = _SECTOR_MIRRORING_HINTS.get(sector, "과거 한국 주식시장의 구체적 사례")

    stock_names = [s.get("stock_name", s["stock_code"]) for s in stocks[:5]]
    stock_str = "·".join(stock_names)

    trend_desc = {"consecutive_rise": "연속 상승", "majority_rise": "상승 우세"}.get(trend_type, "변동")

    # 섹터/매크로 분석 결과 (파이프라인에서 주입됨)
    sector_analysis = theme.get("sector_analysis", "")
    macro_context = theme.get("macro_context", "")

    extra_context = ""
    if sector_analysis:
        extra_context += f"\n섹터 심층 분석:\n{sector_analysis}\n"
    if macro_context:
        extra_context += f"\n거시경제 환경:\n{macro_context}\n"

    prompt = f"""현재 시장 상황을 분석하여 키워드를 생성하세요.

현재:
- 섹터: {sector}
- 종목: {stock_str}
- 트렌드: {trend_desc} ({trend_days}일)
- 변동률: {avg_change:+.1f}%

역사적 참고:
{hint}
{extra_context}
요구사항:
1. 15자 이내 키워드
2. 2-3문장 설명 (섹터 분석과 거시경제 맥락을 반영)

응답 (JSON):
{{"keyword": "키워드", "description": "설명"}}
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        data = json.loads(resp.choices[0].message.content)
        return {
            "title": data.get("keyword", theme.get("title", "")),
            "description": data.get("description", ""),
            "sector": sector,
            "stocks": [s["stock_code"] for s in stocks],
            "trend_days": trend_days,
            "trend_type": trend_type,
            "mirroring_hint": hint,
        }
    except Exception as e:
        print(f"  ⚠️  키워드 생성 실패 (fallback): {e}")
        # Fallback: 템플릿 기반
        return {
            "title": f"{sector} {trend_desc} 신호",
            "description": f"{stock_str} {trend_days}일 {trend_desc}",
            "sector": sector,
            "stocks": [s["stock_code"] for s in stocks],
            "trend_days": trend_days,
            "trend_type": trend_type,
            "mirroring_hint": hint,
        }


def calculate_quality_score(kw):
    """품질 점수 계산."""
    score = 0
    if len(kw.get("stocks", [])) >= 2:
        score += 20
    if kw.get("sector"):
        score += 15
    if kw.get("mirroring_hint"):
        score += 15
    score += min(20, kw.get("trend_days", 0) * 5)
    if re.search(r"20\d{2}", kw.get("description", "")):
        score += 10
    return max(0, min(100, score))


# ============================================================
# 통합 파이프라인
# ============================================================

async def run_integrated_pipeline():
    """Phase 1-4 통합 실행 (예외 처리 포함)."""
    print("=" * 70)
    print("🚀 통합 데이터 파이프라인 시작")
    print("=" * 70)

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY 없음")
        return False

    try:
        # Phase 1: 멀티데이 트렌드
        print("\n[Phase 1] 멀티데이 트렌드 감지")
        try:
            end_date_str, end_date_obj = get_latest_trading_date()
            print(f"  최근 영업일: {end_date_str}")
        except Exception as e:
            print(f"❌ 영업일 확인 실패: {e}")
            return False

        try:
            df_all = fetch_multi_day_data(end_date_str, days=5)
            print(f"  5일 데이터 수집 완료: {len(df_all)}건")
        except Exception as e:
            print(f"❌ 시장 데이터 수집 실패: {e}")
            return False

        trending = calculate_trend_metrics(df_all)
        print(f"  트렌드 감지: {len(trending)}개 종목")

        if len(trending) < 5:
            print(f"⚠️  트렌드 종목 부족 ({len(trending)}개), 최소 5개 필요")
            return False

        selected_stocks = select_top_trending(trending, target=15)
        print(f"  상위 {len(selected_stocks)}개 선택 완료")

        # 종목명 추가
        for s in selected_stocks:
            try:
                s["stock_name"] = pykrx_stock.get_market_ticker_name(s["stock_code"])
            except:
                s["stock_name"] = s["stock_code"]

        # Phase 2: 섹터 클러스터링
        print("\n[Phase 2] 섹터 클러스터링")
        try:
            selected_stocks = await enrich_with_sectors(selected_stocks)
            print(f"  섹터 정보 매핑 완료")
        except Exception as e:
            print(f"⚠️  섹터 매핑 실패 (계속 진행): {e}")
            # 섹터 정보 없어도 계속 진행

        themes = cluster_by_sector(selected_stocks)
        print(f"  생성된 테마: {len(themes)}개")

        selected_themes = select_top_themes(themes, target=5)
        print(f"  상위 {len(selected_themes)}개 테마 선택 완료")

        # Phase 3: RSS 뉴스 매칭
        print("\n[Phase 3] RSS 뉴스 매칭")
        news_map = {}
        try:
            rss = RSSService(RSS_FEEDS)
            news = rss.fetch_top_news_structured()
            print(f"  RSS 뉴스 수집: {len(news)}개")

            if news:
                news = preprocess_news(news)
                print(f"  전처리 완료: {len(news)}개")

                news_map = match_news_to_stocks_llm(selected_stocks, news, openai_key)
                print(f"  뉴스-종목 매칭: {len(news_map)}개")
            else:
                print("  ⚠️  뉴스 없음 (계속 진행)")
        except Exception as e:
            print(f"⚠️  RSS 뉴스 매칭 실패 (계속 진행): {e}")
            # 뉴스 매칭 실패해도 계속 진행

        # Phase 4: 키워드 생성
        print("\n[Phase 4] 테마 키워드 생성")
        keywords = []
        for theme in selected_themes:
            try:
                kw = generate_keyword_llm(theme, openai_key)
                kw["quality_score"] = calculate_quality_score(kw)
                keywords.append(kw)
            except Exception as e:
                print(f"  ⚠️  테마 키워드 생성 실패: {e}")
                # 실패한 테마는 건너뜀

        if not keywords:
            print("❌ 키워드 생성 실패")
            return False

        print(f"  키워드 생성 완료: {len(keywords)}개")

        keywords_sorted = sorted(keywords, key=lambda k: k["quality_score"], reverse=True)
        final_keywords = keywords_sorted[:3]

        # 최소 3개 보장
        if len(final_keywords) < 3:
            print(f"⚠️  키워드 {len(final_keywords)}개만 생성됨, 템플릿 추가")
            # 거래량 TOP 개별 종목으로 보충
            for stock in sorted(selected_stocks, key=lambda s: s["volume"], reverse=True):
                if len(final_keywords) >= 3:
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
                final_keywords.append(fallback_kw)

        print(f"  최종 선택: {len(final_keywords)}개 키워드")

        # DB 저장
        print("\n[저장] DB에 저장 중...")
        try:
            await save_to_db(end_date_obj.date(), selected_stocks, news_map, final_keywords)
        except Exception as e:
            print(f"❌ DB 저장 실패: {e}")
            return False

        # Phase 5: Historical Cases 자동 생성
        print("\n[Phase 5] Historical Cases 생성")
        try:
            from scripts.generate_cases import main as generate_cases_main
            await generate_cases_main()
            print("  ✅ Historical cases 생성 완료")
        except Exception as e:
            print(f"  ⚠️  Historical cases 생성 실패: {e}")
            print("  (키워드는 정상 저장되었으나, 과거 사례 매칭 미완료)")

        print("\n" + "=" * 70)
        print("✅ 통합 파이프라인 완료!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ 파이프라인 치명적 오류: {e}")
        import traceback

        traceback.print_exc()
        return False


async def save_to_db(date, stocks, news_map, keywords):
    """DB 저장."""
    import asyncpg

    db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    if not db_url:
        db_url = "postgresql://narative:password@postgres:5432/narrative_invest"

    conn = await asyncpg.connect(db_url)

    # 시장 지수
    try:
        end_str = date.strftime("%Y%m%d")
        kospi = pykrx_stock.get_index_ohlcv(end_str, end_str, "1001")
        kosdaq = pykrx_stock.get_index_ohlcv(end_str, end_str, "2001")
        market_summary = f"KOSPI {kospi.iloc[0]['종가']:.2f}, KOSDAQ {kosdaq.iloc[0]['종가']:.2f}"
    except:
        market_summary = "시장 지수 조회 중"

    # top_keywords 구조 생성
    top_keywords = {"keywords": []}
    for kw in keywords:
        stock_codes = kw.get("stocks", [])
        stock_names = {s["stock_code"]: s["stock_name"] for s in stocks if s["stock_code"] in stock_codes}

        # news_map에서 카탈리스트 정보 추출
        catalyst = None
        for code in stock_codes:
            if code in news_map:
                catalyst = news_map[code]
                break

        keyword_entry = {
            "title": kw.get("title", ""),
            "description": kw.get("description", ""),
            "category": kw.get("trend_type", ""),
            "tagline": kw.get("sector", ""),
            "sector": kw.get("sector", ""),  # 직접 필드 추가
            "trend_days": kw.get("trend_days", 0),  # 직접 필드 추가
            "trend_type": kw.get("trend_type", ""),  # 직접 필드 추가
            "mirroring_hint": kw.get("mirroring_hint", ""),  # 직접 필드 추가
            "catalyst": catalyst["title"] if catalyst else None,  # 카탈리스트 추가
            "stocks": [
                {
                    "stock_code": code,
                    "stock_name": stock_names.get(code, code),
                    "reason": f"{kw.get('trend_type', '')}, {kw.get('trend_days', 0)}일 트렌드",
                }
                for code in stock_codes
            ],
            "quality_score": kw.get("quality_score", 0),
            "sources": {
                "market_data": {"provider": "pykrx", "date": date.isoformat(), "stocks": stock_codes},
                "sector_info": {"provider": "stock_listings", "sector": kw.get("sector", "")},
                "historical_hint": {"provider": "_SECTOR_MIRRORING_HINTS", "case": kw.get("mirroring_hint", "")},
                "news": [
                    {**catalyst, "citations": catalyst.get("citations", [])}
                    if catalyst else None
                    for catalyst in [news_map.get(code) for code in stock_codes]
                    if catalyst is not None
                ] or ([catalyst] if catalyst else []),  # citations 포함 뉴스 출처
            },
        }
        top_keywords["keywords"].append(keyword_entry)

    # daily_briefings 저장 (idempotency: DELETE + INSERT)
    # 같은 날짜의 기존 데이터 삭제 (briefing_stocks 먼저 삭제 후 daily_briefings 삭제)
    existing_id = await conn.fetchval(
        "SELECT id FROM daily_briefings WHERE briefing_date = $1",
        date
    )
    if existing_id:
        # briefing_stocks 먼저 삭제
        await conn.execute(
            "DELETE FROM briefing_stocks WHERE briefing_id = $1",
            existing_id
        )
        # daily_briefings 삭제
        await conn.execute(
            "DELETE FROM daily_briefings WHERE id = $1",
            existing_id
        )
        print(f"  → 기존 데이터 삭제: daily_briefings id={existing_id}")

    bid = await conn.fetchval(
        "INSERT INTO daily_briefings (briefing_date, market_summary, top_keywords, created_at) "
        "VALUES ($1, $2, $3::jsonb, NOW()) RETURNING id",
        date,
        market_summary,
        json.dumps(top_keywords, ensure_ascii=False),
    )
    print(f"  → daily_briefings 저장: id={bid}")

    # briefing_stocks 저장
    rows = []
    for s in stocks:
        catalyst_info = news_map.get(s["stock_code"])
        catalyst_dt = None
        if catalyst_info:
            try:
                dt = datetime.fromisoformat(catalyst_info["published_at"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                catalyst_dt = dt
            except:
                pass

        rows.append((
            bid,
            s["stock_code"],
            s["stock_name"],
            s["change_rate"],
            s["volume"],
            s["trend_type"],
            datetime.now(),
            s["trend_days"],
            s["trend_type"],
            catalyst_info["title"] if catalyst_info else None,
            catalyst_info["url"] if catalyst_info else None,
            catalyst_dt,
            catalyst_info["source"] if catalyst_info else None,
        ))

    await conn.executemany(
        "INSERT INTO briefing_stocks "
        "(briefing_id, stock_code, stock_name, change_rate, volume, selection_reason, created_at, "
        "trend_days, trend_type, catalyst, catalyst_url, catalyst_published_at, catalyst_source) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)",
        rows,
    )
    print(f"  → briefing_stocks 저장: {len(rows)}건")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(run_integrated_pipeline())
