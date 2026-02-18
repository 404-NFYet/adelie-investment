"""한국투자증권(KIS) API 서비스.

모의투자 전용 - 실시간 시세, 종목 검색, 차트 데이터 제공.
Rate limit: 초당 2건 (모의투자) -> Redis 캐싱 + 백그라운드 갱신으로 대응.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.services.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)

# 캐시 TTL 전략
CACHE_TTL = {
    "price": 30,         # 개별 종목 현재가: 30초
    "search": 300,       # 종목 검색 결과: 5분
    "chart_intra": 60,   # 분봉 차트: 1분
    "chart_daily": 3600, # 일봉 차트: 1시간
    "ranking": 60,       # 랭킹: 1분
    "token": 86000,      # OAuth 토큰: ~24시간
}


class KISService:
    """한국투자증권 API 클라이언트 (모의투자 전용)."""

    def __init__(self):
        # HANTU_* 키 또는 KIS_* 키 모두 지원
        self.app_key = os.getenv("KIS_APP_KEY") or os.getenv("HANTU_APP_KEY", "")
        self.app_secret = os.getenv("KIS_APP_SECRET") or os.getenv("HANTU_APP_SECRET", "")
        # 모의투자 API 엔드포인트
        self.base_url = "https://openapivts.koreainvestment.com:29443"
        self.client = httpx.AsyncClient(
            timeout=10,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._token_lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        """API 키가 설정되어 있는지 확인."""
        return bool(self.app_key and self.app_secret)

    async def get_token(self) -> str:
        """OAuth 토큰 발급 (24시간 유효, 캐싱)."""
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token

        async with self._token_lock:
            # 락 획득 후 재확인 (다른 코루틴이 갱신했을 수 있음)
            if self._token and self._token_expires and datetime.now() < self._token_expires:
                return self._token

            # Redis 캐시 확인 (멀티 인스턴스에서 재사용)
            cache = await get_redis_cache()
            if cache.client:
                cached = await cache.client.get("kis:token")
                if cached:
                    self._token = cached
                    self._token_expires = datetime.now() + timedelta(hours=23)
                    return self._token

            if not self.is_configured:
                raise ValueError("KIS API 키가 설정되지 않았습니다")

            # 토큰 발급 API 호출 (재사용 클라이언트)
            response = await self.client.post(
                f"{self.base_url}/oauth2/tokenP",
                json={
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                },
            )
            data = response.json()
            self._token = data.get("access_token", "")
            self._token_expires = datetime.now() + timedelta(hours=23)

            # Redis에 캐싱
            if cache.client and self._token:
                await cache.client.setex("kis:token", CACHE_TTL["token"], self._token)

            return self._token

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """API 요청 헬퍼."""
        token = await self.get_token()
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "Content-Type": "application/json; charset=utf-8",
        }
        kwargs.setdefault("headers", {}).update(headers)

        # 실제 KIS API 호출 (재사용 클라이언트)
        response = await self.client.request(method, f"{self.base_url}{path}", **kwargs)
        if response.status_code >= 400:
            logger.error("KIS API error (%s): %s", response.status_code, response.text[:200])
        return response.json()

    async def get_current_price(self, stock_code: str) -> Optional[dict]:
        """실시간 현재가 조회 (캐싱 적용)."""
        cache = await get_redis_cache()
        cache_key = f"kis:price:{stock_code}"

        # 캐시 확인
        if cache.client:
            try:
                cached = await cache.client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        try:
            # API 키가 없으면 KIS 호출 불가
            if not self.is_configured:
                return None

            # KIS 현재가 API 호출
            data = await self._request(
                "GET",
                "/uapi/domestic-stock/v1/quotations/inquire-price",
                params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code},
                headers={"tr_id": "FHKST01010100"},
            )

            output = data.get("output", {})
            if not output:
                return None

            result = {
                "stock_code": stock_code,
                "stock_name": output.get("hts_kor_isnm", stock_code),
                "current_price": int(output.get("stck_prpr", 0)),
                "change_rate": float(output.get("prdy_ctrt", 0)),
                "volume": int(output.get("acml_vol", 0)),
                "high": int(output.get("stck_hgpr", 0)),
                "low": int(output.get("stck_lwpr", 0)),
                "timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
            }

            # 캐시 저장
            if cache.client:
                await cache.client.setex(cache_key, CACHE_TTL["price"], json.dumps(result))

            return result
        except Exception as e:
            logger.error(f"KIS 현재가 조회 실패 ({stock_code}): {e}")
            return None

    async def search_stocks(self, query: str) -> list[dict]:
        """종목 검색 (캐싱 적용)."""
        cache = await get_redis_cache()
        cache_key = f"kis:search:{query}"

        if cache.client:
            try:
                cached = await cache.client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        # KIS API 종목 검색이 제한적이므로 pykrx ticker list 기반 로컬 검색
        try:
            from pykrx import stock
            tickers = stock.get_market_ticker_list(datetime.now().strftime("%Y%m%d"))
            results = []
            for ticker in tickers:
                name = stock.get_market_ticker_name(ticker)
                if query.lower() in name.lower() or query in ticker:
                    results.append({
                        "stock_code": ticker,
                        "stock_name": name,
                        "market": "KOSPI" if len(ticker) == 6 and ticker[0] in "012345" else "KOSDAQ",
                    })
                    if len(results) >= 20:
                        break

            if cache.client and results:
                await cache.client.setex(cache_key, CACHE_TTL["search"], json.dumps(results))

            return results
        except Exception as e:
            logger.error(f"종목 검색 실패 ({query}): {e}")
            return []

    async def get_ranking(self, rank_type: str = "volume") -> list[dict]:
        """종목 랭킹 (거래량/등락률, 캐싱 적용)."""
        cache = await get_redis_cache()
        cache_key = f"kis:ranking:{rank_type}"

        if cache.client:
            try:
                cached = await cache.client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        try:
            from pykrx import stock
            today = datetime.now().strftime("%Y%m%d")

            if rank_type == "volume":
                df = stock.get_market_ohlcv_by_ticker(today)
                if df.empty:
                    df = stock.get_market_ohlcv_by_ticker((datetime.now() - timedelta(days=1)).strftime("%Y%m%d"))
                df = df.sort_values("거래량", ascending=False).head(10)
            else:  # gainers or losers
                df = stock.get_market_ohlcv_by_ticker(today)
                if df.empty:
                    df = stock.get_market_ohlcv_by_ticker((datetime.now() - timedelta(days=1)).strftime("%Y%m%d"))
                if rank_type == "gainers":
                    df = df.sort_values("등락률", ascending=False).head(10)
                else:
                    df = df.sort_values("등락률", ascending=True).head(10)

            results = []
            for ticker, row in df.iterrows():
                name = stock.get_market_ticker_name(ticker)
                results.append({
                    "stock_code": ticker,
                    "stock_name": name,
                    "current_price": int(row.get("종가", 0)),
                    "change_rate": round(float(row.get("등락률", 0)), 2),
                    "volume": int(row.get("거래량", 0)),
                })

            if cache.client and results:
                await cache.client.setex(cache_key, CACHE_TTL["ranking"], json.dumps(results))

            return results
        except Exception as e:
            logger.error(f"랭킹 조회 실패 ({rank_type}): {e}")
            return []


# 싱글톤
_kis_service: Optional[KISService] = None


def get_kis_service() -> KISService:
    """KIS 서비스 싱글톤 반환."""
    global _kis_service
    if _kis_service is None:
        _kis_service = KISService()
    return _kis_service


async def close_kis_service() -> None:
    """KIS 서비스 클라이언트 종료."""
    global _kis_service
    if _kis_service and getattr(_kis_service, "client", None):
        await _kis_service.client.aclose()
