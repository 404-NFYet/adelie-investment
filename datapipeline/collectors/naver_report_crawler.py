"""네이버 증권 종목분석 리포트 크롤러.

네이버 금융 리서치 페이지에서 종목분석 리포트 목록을 수집한다.
"""

from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

STOCK_REPORT_URL = "https://finance.naver.com/research/company_list.naver"
BASE_URL = "https://finance.naver.com"


@dataclass
class StockReport:
    """종목분석 리포트."""
    stock_name: str
    title: str
    broker: str
    pdf_url: str
    date: str
    target_price: str = ""
    opinion: str = ""


async def fetch_report_list(page: int = 1) -> list[StockReport]:
    """종목분석 리포트 목록 조회 (단일 페이지).

    Args:
        page: 페이지 번호

    Returns:
        StockReport 리스트
    """
    url = f"{STOCK_REPORT_URL}?&page={page}"
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        resp.encoding = "euc-kr"

    return _parse_report_page(resp.text)


async def collect_reports(pages: int = 1, download: bool = False) -> list[StockReport]:
    """여러 페이지의 종목분석 리포트 수집.

    Args:
        pages: 수집할 페이지 수
        download: PDF 다운로드 여부 (현재 미사용)

    Returns:
        StockReport 리스트
    """
    all_reports: list[StockReport] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        for page in range(1, pages + 1):
            url = f"{STOCK_REPORT_URL}?&page={page}"
            resp = await client.get(url)
            resp.encoding = "euc-kr"
            reports = _parse_report_page(resp.text)
            all_reports.extend(reports)

    return all_reports


def _parse_report_page(html: str) -> list[StockReport]:
    """HTML에서 종목분석 리포트 파싱."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.type_1 tr")
    reports = []

    for row in rows:
        cols = row.select("td")
        if len(cols) < 6:
            continue

        stock_name = cols[0].get_text(strip=True)
        if not stock_name:
            continue

        title = cols[1].get_text(strip=True)
        broker = cols[2].get_text(strip=True)
        opinion = cols[3].get_text(strip=True)
        target_price = cols[4].get_text(strip=True)
        date_text = cols[5].get_text(strip=True)

        # PDF 링크
        pdf_link = cols[1].select_one("a")
        pdf_url = ""
        if pdf_link and pdf_link.get("href"):
            href = pdf_link["href"]
            pdf_url = BASE_URL + href if href.startswith("/") else href

        reports.append(StockReport(
            stock_name=stock_name,
            title=title,
            broker=broker,
            pdf_url=pdf_url,
            date=date_text,
            target_price=target_price,
            opinion=opinion,
        ))

    return reports
