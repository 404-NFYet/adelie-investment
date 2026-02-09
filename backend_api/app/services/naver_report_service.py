"""Naver Finance Report Crawler - 네이버 증권 리포트 수집."""
import asyncio
import re
from datetime import date, datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import urljoin, urlencode

import httpx
from bs4 import BeautifulSoup


@dataclass
class NaverReport:
    """네이버 증권 리포트 데이터 모델."""
    title: str
    broker: str  # 증권사명
    pdf_url: str
    published_date: date
    report_type: str  # industry 또는 economy
    target_industry: Optional[str] = None  # 산업분석의 경우 대상 업종


class NaverReportService:
    """네이버 증권 리서치 리포트 크롤러.
    
    지원 페이지:
    - 산업분석: https://finance.naver.com/research/industry_list.naver
    - 경제분석: https://finance.naver.com/research/economy_list.naver
    """
    
    BASE_URL = "https://finance.naver.com"
    INDUSTRY_URL = f"{BASE_URL}/research/industry_list.naver"
    ECONOMY_URL = f"{BASE_URL}/research/economy_list.naver"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """페이지 HTML 가져오기."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                print(f"[NaverReportService] Error fetching {url}: {e}")
                return None
    
    def parse_date(self, date_str: str) -> Optional[date]:
        """날짜 문자열 파싱 (YY.MM.DD 형식)."""
        try:
            date_str = date_str.strip()
            parts = date_str.split(".")
            if len(parts) == 3:
                year = int(parts[0])
                if year < 100:
                    year += 2000
                return date(year, int(parts[1]), int(parts[2]))
        except Exception:
            pass
        return None
    
    def parse_industry_list(self, html: str, target_date: date) -> List[NaverReport]:
        """산업분석 리스트 페이지 파싱."""
        reports = []
        soup = BeautifulSoup(html, "html.parser")
        
        table = soup.find("table", class_="type_1")
        if not table:
            return reports
        
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            
            try:
                industry_cell = cells[0]
                industry = industry_cell.get_text(strip=True) if industry_cell else ""
                
                title_cell = cells[1]
                title_link = title_cell.find("a")
                if not title_link:
                    continue
                title = title_link.get_text(strip=True)
                
                onclick = title_link.get("onclick", "")
                pdf_match = re.search(r"javascript:research_read\('(\d+)',", onclick)
                pdf_url = ""
                if pdf_match:
                    report_id = pdf_match.group(1)
                    pdf_url = f"{self.BASE_URL}/research/industry_read.naver?nid={report_id}"
                
                broker_cell = cells[2]
                broker = broker_cell.get_text(strip=True) if broker_cell else ""
                
                date_cell = cells[4]
                date_str = date_cell.get_text(strip=True) if date_cell else ""
                pub_date = self.parse_date(date_str)
                
                if pub_date and pub_date == target_date:
                    reports.append(NaverReport(
                        title=title,
                        broker=broker,
                        pdf_url=pdf_url,
                        published_date=pub_date,
                        report_type="industry",
                        target_industry=industry,
                    ))
            except Exception:
                continue
        
        return reports
    
    def parse_economy_list(self, html: str, target_date: date) -> List[NaverReport]:
        """경제분석 리스트 페이지 파싱."""
        reports = []
        soup = BeautifulSoup(html, "html.parser")
        
        table = soup.find("table", class_="type_1")
        if not table:
            return reports
        
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            
            try:
                title_cell = cells[0]
                title_link = title_cell.find("a")
                if not title_link:
                    continue
                title = title_link.get_text(strip=True)
                
                onclick = title_link.get("onclick", "")
                pdf_match = re.search(r"javascript:research_read\('(\d+)',", onclick)
                pdf_url = ""
                if pdf_match:
                    report_id = pdf_match.group(1)
                    pdf_url = f"{self.BASE_URL}/research/economy_read.naver?nid={report_id}"
                
                broker_cell = cells[1]
                broker = broker_cell.get_text(strip=True) if broker_cell else ""
                
                date_cell = cells[3]
                date_str = date_cell.get_text(strip=True) if date_cell else ""
                pub_date = self.parse_date(date_str)
                
                if pub_date and pub_date == target_date:
                    reports.append(NaverReport(
                        title=title,
                        broker=broker,
                        pdf_url=pdf_url,
                        published_date=pub_date,
                        report_type="economy",
                    ))
            except Exception:
                continue
        
        return reports
    
    async def fetch_reports_by_date(
        self, target_date: date, report_type: str = "all", max_pages: int = 5
    ) -> List[NaverReport]:
        """특정 날짜의 모든 리포트 수집."""
        reports = []
        
        if report_type in ("industry", "all"):
            for page in range(1, max_pages + 1):
                url = f"{self.INDUSTRY_URL}?&page={page}"
                html = await self.fetch_page(url)
                if not html:
                    break
                
                page_reports = self.parse_industry_list(html, target_date)
                reports.extend(page_reports)
                
                if not page_reports:
                    break
                
                await asyncio.sleep(0.5)
        
        if report_type in ("economy", "all"):
            for page in range(1, max_pages + 1):
                url = f"{self.ECONOMY_URL}?&page={page}"
                html = await self.fetch_page(url)
                if not html:
                    break
                
                page_reports = self.parse_economy_list(html, target_date)
                reports.extend(page_reports)
                
                if not page_reports:
                    break
                
                await asyncio.sleep(0.5)
        
        return reports
    
    async def fetch_report_detail(self, report: NaverReport) -> Optional[Dict]:
        """개별 리포트 상세 정보 및 PDF URL 추출."""
        if not report.pdf_url:
            return None
        
        html = await self.fetch_page(report.pdf_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, "html.parser")
        
        pdf_link = soup.find("a", href=re.compile(r"\.pdf"))
        pdf_download_url = pdf_link.get("href") if pdf_link else None
        
        content_div = soup.find("div", class_="view_cnt")
        summary = content_div.get_text(strip=True) if content_div else ""
        
        return {
            "title": report.title,
            "broker": report.broker,
            "published_date": report.published_date.isoformat(),
            "report_type": report.report_type,
            "target_industry": report.target_industry,
            "pdf_download_url": pdf_download_url,
            "summary": summary[:500] if summary else "",
        }


_instance: Optional[NaverReportService] = None


def get_naver_report_service() -> NaverReportService:
    """NaverReportService 싱글톤 인스턴스 반환."""
    global _instance
    if _instance is None:
        _instance = NaverReportService()
    return _instance
