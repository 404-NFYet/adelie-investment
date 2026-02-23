"""
DART Client - 금융감독원 전자공시 API 클라이언트

OpenDART API를 통해 기업 공시 정보, 재무제표 등을 조회합니다.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("narrative_api.dart_client")

DART_BASE_URL = "https://opendart.fss.or.kr/api"


class DartClient:
    """OpenDART API 클라이언트"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_settings().OPEN_DART_API_KEY
        self._corp_code_cache: dict[str, str] = {}

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any],
        timeout: float = 10.0,
    ) -> dict:
        """DART API 요청"""
        if not self.api_key:
            return {"status": "error", "message": "DART API key not configured"}

        params["crtfc_key"] = self.api_key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{DART_BASE_URL}/{endpoint}",
                    params=params,
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") not in ("000", "013"):
                    logger.warning(f"DART API error: {data.get('message')}")

                return data
        except httpx.HTTPError as e:
            logger.error(f"DART API request failed: {e}")
            return {"status": "error", "message": str(e)}

    async def get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목 코드로 기업 고유번호 조회"""
        if stock_code in self._corp_code_cache:
            return self._corp_code_cache[stock_code]

        return None

    async def get_recent_disclosures(
        self,
        stock_code: str,
        days: int = 30,
        limit: int = 10,
    ) -> dict:
        """
        최근 공시 목록 조회

        Args:
            stock_code: 종목 코드 (6자리)
            days: 조회 기간 (일)
            limit: 최대 조회 건수

        Returns:
            공시 목록
        """
        end_date = datetime.now()
        begin_date = end_date - timedelta(days=days)

        params = {
            "corp_code": stock_code,
            "bgn_de": begin_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_count": str(limit),
        }

        result = await self._request("list.json", params)

        if result.get("status") != "000":
            return {
                "success": False,
                "message": result.get("message", "공시 조회 실패"),
                "disclosures": [],
            }

        disclosures = []
        for item in result.get("list", [])[:limit]:
            disclosures.append({
                "rcept_no": item.get("rcept_no"),
                "rcept_dt": item.get("rcept_dt"),
                "report_nm": item.get("report_nm"),
                "corp_name": item.get("corp_name"),
                "flr_nm": item.get("flr_nm"),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no')}",
            })

        return {
            "success": True,
            "stock_code": stock_code,
            "total_count": result.get("total_count", len(disclosures)),
            "disclosures": disclosures,
        }

    async def get_financial_statements(
        self,
        stock_code: str,
        year: Optional[int] = None,
        report_code: str = "11011",
    ) -> dict:
        """
        재무제표 조회

        Args:
            stock_code: 종목 코드 (6자리)
            year: 사업연도 (기본값: 전년)
            report_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11014: 분기보고서)

        Returns:
            재무제표 데이터
        """
        if year is None:
            year = datetime.now().year - 1

        params = {
            "corp_code": stock_code,
            "bsns_year": str(year),
            "reprt_code": report_code,
        }

        result = await self._request("fnlttSinglAcnt.json", params)

        if result.get("status") != "000":
            return {
                "success": False,
                "message": result.get("message", "재무제표 조회 실패"),
                "financials": {},
            }

        financials = {}
        for item in result.get("list", []):
            account_nm = item.get("account_nm", "")
            thstrm_amount = item.get("thstrm_amount", "")
            try:
                amount = int(thstrm_amount.replace(",", "")) if thstrm_amount else 0
            except (ValueError, AttributeError):
                amount = 0

            if "매출" in account_nm:
                financials["revenue"] = amount
            elif "영업이익" in account_nm:
                financials["operating_profit"] = amount
            elif "당기순이익" in account_nm:
                financials["net_income"] = amount
            elif "자산총계" in account_nm:
                financials["total_assets"] = amount
            elif "부채총계" in account_nm:
                financials["total_liabilities"] = amount
            elif "자본총계" in account_nm:
                financials["total_equity"] = amount

        return {
            "success": True,
            "stock_code": stock_code,
            "year": year,
            "financials": financials,
        }

    async def get_major_shareholders(self, stock_code: str) -> dict:
        """
        주요 주주 현황 조회

        Args:
            stock_code: 종목 코드 (6자리)

        Returns:
            주요 주주 정보
        """
        params = {"corp_code": stock_code}
        result = await self._request("hyslrSttus.json", params)

        if result.get("status") != "000":
            return {
                "success": False,
                "message": result.get("message", "주주 현황 조회 실패"),
                "shareholders": [],
            }

        shareholders = []
        for item in result.get("list", []):
            shareholders.append({
                "nm": item.get("nm"),
                "relate": item.get("relate"),
                "stock_kind": item.get("stock_knd"),
                "bsis_posesn_stock_co": item.get("bsis_posesn_stock_co"),
                "bsis_posesn_stock_qota_rt": item.get("bsis_posesn_stock_qota_rt"),
            })

        return {
            "success": True,
            "stock_code": stock_code,
            "shareholders": shareholders,
        }


async def get_dart_client() -> DartClient:
    """DartClient 인스턴스 반환"""
    return DartClient()


async def format_dart_for_chat(stock_code: str, stock_name: str = "") -> str:
    """채팅용 DART 정보 포맷팅"""
    client = await get_dart_client()

    disclosure_result = await client.get_recent_disclosures(stock_code, days=30, limit=5)
    financial_result = await client.get_financial_statements(stock_code)

    lines = []
    title = stock_name if stock_name else stock_code
    lines.append(f"### 📋 {title} DART 공시 정보\n")

    if disclosure_result.get("success") and disclosure_result.get("disclosures"):
        lines.append("**최근 공시**")
        for disc in disclosure_result["disclosures"][:5]:
            lines.append(f"- [{disc['rcept_dt']}] {disc['report_nm']}")
        lines.append("")

    if financial_result.get("success") and financial_result.get("financials"):
        fin = financial_result["financials"]
        lines.append(f"**{financial_result.get('year')}년 재무 하이라이트**")
        if fin.get("revenue"):
            lines.append(f"- 매출액: {fin['revenue']:,}원")
        if fin.get("operating_profit"):
            lines.append(f"- 영업이익: {fin['operating_profit']:,}원")
        if fin.get("net_income"):
            lines.append(f"- 당기순이익: {fin['net_income']:,}원")

    if not lines[1:]:
        lines.append("_공시 정보를 찾을 수 없습니다._")

    return "\n".join(lines)
