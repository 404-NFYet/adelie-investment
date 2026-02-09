"""네이버 증권 경제 분석 리포트 크롤러.

네이버 금융의 경제 분석 리포트 목록을 수집한다.
날짜별 필터링, PDF 다운로드를 지원.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://finance.naver.com"
ECONOMY_URL = f"{BASE_URL}/research/economy_list.naver"


@dataclass
class EconomyReport:
    """경제 분석 리포트."""

    title: str
    broker: str         # 증권사명
    pdf_url: str
    date: str
    views: int = 0


class NaverEconomyCrawler:
    """네이버 증권 경제 분석 리포트 크롤러."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
            follow_redirects=True,
        )

    async def fetch_reports(self, target_date: str, max_pages: int = 20) -> list[EconomyReport]:
        """특정 날짜의 경제 분석 리포트 수집.

        Args:
            target_date: "YYYY.MM.DD" or "YYYYMMDD" 형식
            max_pages: 최대 페이지 수
        """
        reports: list[EconomyReport] = []
        target = self._normalize_date(target_date)

        for page in range(1, max_pages + 1):
            url = f"{ECONOMY_URL}?&page={page}"
            try:
                resp = await self.client.get(url)
                resp.encoding = "euc-kr"
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception as exc:
                LOGGER.warning("경제 리포트 페이지 %d 실패: %s", page, exc)
                break

            rows = soup.select("table.type_1 tr")
            past_target = False

            for row in rows:
                cols = row.select("td")
                if len(cols) < 4:
                    continue

                date_text = cols[3].get_text(strip=True)
                if not date_text:
                    continue

                if date_text == target:
                    title = cols[0].get_text(strip=True)
                    broker = cols[1].get_text(strip=True)

                    pdf_link = cols[0].select_one("a")
                    pdf_url = ""
                    if pdf_link and pdf_link.get("href"):
                        href = pdf_link["href"]
                        pdf_url = BASE_URL + href if href.startswith("/") else href

                    views = 0
                    try:
                        views = int(cols[2].get_text(strip=True).replace(",", "") or 0)
                    except ValueError:
                        pass

                    reports.append(EconomyReport(
                        title=title, broker=broker,
                        pdf_url=pdf_url, date=date_text, views=views,
                    ))
                elif date_text < target:
                    past_target = True

            if past_target or not rows:
                break

        LOGGER.info("경제 리포트 수집: %s, %d건", target, len(reports))
        return reports

    async def download_pdf(self, pdf_url: str) -> bytes:
        """PDF 파일 다운로드."""
        resp = await self.client.get(pdf_url)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """날짜 포맷 정규화 -> YY.MM.DD."""
        clean = date_str.replace("-", "").replace(".", "").strip()
        if len(clean) == 8:
            return f"{clean[2:4]}.{clean[4:6]}.{clean[6:8]}"
        return date_str

    async def close(self) -> None:
        """HTTP 클라이언트 정리."""
        await self.client.aclose()
