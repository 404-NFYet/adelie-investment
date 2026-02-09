"""네이버 증권 리포트 크롤러 모듈
산업 분석 + 경제 분석 리포트 수집 (모듈화만, 파이프라인 미통합)
"""
import httpx
from dataclasses import dataclass
from datetime import date
from typing import Optional
import re
from bs4 import BeautifulSoup


@dataclass
class IndustryReport:
    """산업 분석 리포트"""
    category: str        # 분류 (반도체, 자동차 등)
    title: str
    broker: str          # 증권사명
    pdf_url: str
    date: str
    views: int = 0


@dataclass
class EconomyReport:
    """경제 분석 리포트"""
    title: str
    broker: str
    pdf_url: str
    date: str
    views: int = 0


class NaverReportCrawler:
    INDUSTRY_URL = "https://finance.naver.com/research/industry_list.naver"
    ECONOMY_URL = "https://finance.naver.com/research/economy_list.naver"
    BASE_URL = "https://finance.naver.com"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30.0,
            follow_redirects=True,
        )

    async def fetch_industry_reports(self, target_date: str) -> list[IndustryReport]:
        """산업 분석 리포트 수집 (모든 증권사, 특정 날짜)

        Args:
            target_date: "YYYY.MM.DD" or "YYYYMMDD" format
        """
        reports = []
        page = 1
        target = self._normalize_date(target_date)

        while True:
            url = f"{self.INDUSTRY_URL}?&page={page}"
            resp = await self.client.get(url)
            resp.encoding = "euc-kr"
            soup = BeautifulSoup(resp.text, "html.parser")

            rows = soup.select("table.type_1 tr")
            found_target = False
            past_target = False

            for row in rows:
                cols = row.select("td")
                if len(cols) < 5:
                    continue

                date_text = cols[4].get_text(strip=True)
                if not date_text:
                    continue

                if date_text == target:
                    found_target = True
                    category = cols[0].get_text(strip=True)
                    title = cols[1].get_text(strip=True)
                    broker = cols[2].get_text(strip=True)

                    # PDF 링크 추출
                    pdf_link = cols[1].select_one("a")
                    pdf_url = ""
                    if pdf_link and pdf_link.get("href"):
                        pdf_url = self.BASE_URL + pdf_link["href"] if pdf_link["href"].startswith("/") else pdf_link["href"]

                    views = int(cols[3].get_text(strip=True).replace(",", "") or 0)

                    reports.append(IndustryReport(
                        category=category, title=title, broker=broker,
                        pdf_url=pdf_url, date=date_text, views=views,
                    ))
                elif date_text < target:
                    past_target = True

            if past_target or not rows or page > 20:
                break
            page += 1

        return reports

    async def fetch_economy_reports(self, target_date: str) -> list[EconomyReport]:
        """경제 분석 리포트 수집"""
        reports = []
        page = 1
        target = self._normalize_date(target_date)

        while True:
            url = f"{self.ECONOMY_URL}?&page={page}"
            resp = await self.client.get(url)
            resp.encoding = "euc-kr"
            soup = BeautifulSoup(resp.text, "html.parser")

            rows = soup.select("table.type_1 tr")
            found_target = False
            past_target = False

            for row in rows:
                cols = row.select("td")
                if len(cols) < 4:
                    continue

                date_text = cols[3].get_text(strip=True)
                if not date_text:
                    continue

                if date_text == target:
                    found_target = True
                    title = cols[0].get_text(strip=True)
                    broker = cols[1].get_text(strip=True)

                    pdf_link = cols[0].select_one("a")
                    pdf_url = ""
                    if pdf_link and pdf_link.get("href"):
                        pdf_url = self.BASE_URL + pdf_link["href"] if pdf_link["href"].startswith("/") else pdf_link["href"]

                    views = int(cols[2].get_text(strip=True).replace(",", "") or 0)

                    reports.append(EconomyReport(
                        title=title, broker=broker,
                        pdf_url=pdf_url, date=date_text, views=views,
                    ))
                elif date_text < target:
                    past_target = True

            if past_target or not rows or page > 20:
                break
            page += 1

        return reports

    async def download_pdf(self, pdf_url: str) -> bytes:
        """PDF 다운로드"""
        resp = await self.client.get(pdf_url)
        resp.raise_for_status()
        return resp.content

    def _normalize_date(self, date_str: str) -> str:
        """날짜 포맷 정규화 -> YY.MM.DD"""
        clean = date_str.replace("-", "").replace(".", "").strip()
        if len(clean) == 8:
            return f"{clean[2:4]}.{clean[4:6]}.{clean[6:8]}"
        return date_str

    async def close(self):
        await self.client.aclose()
