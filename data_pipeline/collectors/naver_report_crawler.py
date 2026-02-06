"""
네이버 금융 리서치 리포트 크롤러
- 리포트 목록 조회
- PDF 다운로드
- MinIO 업로드 (선택적)
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 네이버 금융 리서치 URL
NAVER_RESEARCH_URL = "https://finance.naver.com/research/"
REPORT_LIST_URL = "https://finance.naver.com/research/company_list.naver"

# User-Agent 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass
class Report:
    """리포트 데이터 클래스"""
    title: str
    stock_name: str
    stock_code: Optional[str]
    broker: str
    date: str
    pdf_url: str
    target_price: Optional[str] = None
    opinion: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "stock_name": self.stock_name,
            "stock_code": self.stock_code,
            "broker": self.broker,
            "date": self.date,
            "pdf_url": self.pdf_url,
            "target_price": self.target_price,
            "opinion": self.opinion
        }


async def fetch_report_list(
    page: int = 1,
    stock_code: Optional[str] = None
) -> list[Report]:
    """
    네이버 금융 리서치 리포트 목록 조회
    
    Args:
        page: 페이지 번호
        stock_code: 종목 코드 (선택)
        
    Returns:
        list[Report]: 리포트 목록
    """
    params = {"page": page}
    if stock_code:
        params["searchType"] = "itemCode"
        params["itemCode"] = stock_code
    
    reports = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                REPORT_LIST_URL,
                params=params,
                headers=HEADERS
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 리포트 테이블 파싱
            table = soup.find("table", class_="type_1")
            if not table:
                logger.warning("Report table not found")
                return reports
            
            rows = table.find_all("tr")
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue
                
                try:
                    # 종목명 및 코드
                    stock_link = cols[0].find("a")
                    if not stock_link:
                        continue
                    
                    stock_name = stock_link.get_text(strip=True)
                    href = stock_link.get("href", "")
                    code_match = re.search(r"code=(\d+)", href)
                    stock_code_parsed = code_match.group(1) if code_match else None
                    
                    # 리포트 제목 및 PDF 링크
                    title_link = cols[1].find("a")
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    pdf_href = title_link.get("href", "")
                    
                    # PDF URL 추출
                    pdf_url = ""
                    if "nid=" in pdf_href:
                        # 상세 페이지에서 PDF URL 추출 필요
                        detail_url = urljoin(NAVER_RESEARCH_URL, pdf_href)
                        pdf_url = await _extract_pdf_url(client, detail_url)
                    
                    # 증권사
                    broker = cols[2].get_text(strip=True)
                    
                    # 목표가/의견
                    target_price = cols[3].get_text(strip=True) or None
                    opinion = cols[4].get_text(strip=True) or None
                    
                    # 날짜
                    date = cols[5].get_text(strip=True)
                    
                    report = Report(
                        title=title,
                        stock_name=stock_name,
                        stock_code=stock_code_parsed,
                        broker=broker,
                        date=date,
                        pdf_url=pdf_url,
                        target_price=target_price,
                        opinion=opinion
                    )
                    reports.append(report)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse row: {e}")
                    continue
            
            logger.info(f"Fetched {len(reports)} reports from page {page}")
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching report list: {e}")
            raise
    
    return reports


async def _extract_pdf_url(client: httpx.AsyncClient, detail_url: str) -> str:
    """
    리포트 상세 페이지에서 PDF URL 추출
    
    Args:
        client: httpx 클라이언트
        detail_url: 상세 페이지 URL
        
    Returns:
        str: PDF URL
    """
    try:
        response = await client.get(detail_url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # PDF 다운로드 링크 찾기
        download_link = soup.find("a", href=re.compile(r"\.pdf", re.I))
        if download_link:
            return download_link.get("href", "")
        
        # iframe 내 PDF 링크 찾기
        iframe = soup.find("iframe", src=re.compile(r"\.pdf", re.I))
        if iframe:
            return iframe.get("src", "")
        
        return ""
        
    except Exception as e:
        logger.warning(f"Failed to extract PDF URL from {detail_url}: {e}")
        return ""


async def download_pdf(
    pdf_url: str,
    output_dir: str = "./downloads",
    filename: Optional[str] = None
) -> Optional[str]:
    """
    PDF 파일 다운로드
    
    Args:
        pdf_url: PDF URL
        output_dir: 저장 디렉토리
        filename: 파일명 (선택)
        
    Returns:
        Optional[str]: 저장된 파일 경로
    """
    if not pdf_url:
        logger.warning("Empty PDF URL")
        return None
    
    # 출력 디렉토리 생성
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 파일명 생성
    if not filename:
        filename = pdf_url.split("/")[-1]
        if not filename.endswith(".pdf"):
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    output_path = os.path.join(output_dir, filename)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(pdf_url, headers=HEADERS, follow_redirects=True)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            logger.info(f"Downloaded PDF to {output_path}")
            return output_path
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to download PDF: {e}")
            return None


async def upload_to_minio(
    file_path: str,
    bucket: str = "reports",
    object_name: Optional[str] = None
) -> Optional[str]:
    """
    MinIO에 파일 업로드 (선택적)
    
    Args:
        file_path: 파일 경로
        bucket: 버킷 이름
        object_name: 객체 이름 (선택)
        
    Returns:
        Optional[str]: 업로드된 객체 URL
    """
    try:
        from minio import Minio
        
        # MinIO 클라이언트 설정 (환경변수에서)
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        client = Minio(
            minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=minio_secure
        )
        
        # 버킷 생성 (없으면)
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        
        # 객체 이름
        if not object_name:
            object_name = os.path.basename(file_path)
        
        # 업로드
        client.fput_object(bucket, object_name, file_path)
        
        url = f"{'https' if minio_secure else 'http'}://{minio_endpoint}/{bucket}/{object_name}"
        logger.info(f"Uploaded to MinIO: {url}")
        
        return url
        
    except ImportError:
        logger.warning("minio package not installed. Skipping MinIO upload.")
        return None
    except Exception as e:
        logger.error(f"Failed to upload to MinIO: {e}")
        return None


async def collect_reports(
    pages: int = 1,
    stock_code: Optional[str] = None,
    download: bool = False,
    output_dir: str = "./downloads"
) -> list[dict]:
    """
    리포트 수집 메인 함수
    
    Args:
        pages: 수집할 페이지 수
        stock_code: 종목 코드 필터 (선택)
        download: PDF 다운로드 여부
        output_dir: 다운로드 디렉토리
        
    Returns:
        list[dict]: 수집된 리포트 목록
    """
    all_reports = []
    
    for page in range(1, pages + 1):
        reports = await fetch_report_list(page=page, stock_code=stock_code)
        
        for report in reports:
            report_dict = report.to_dict()
            
            if download and report.pdf_url:
                # PDF 다운로드
                safe_filename = re.sub(r'[^\w\-_.]', '_', f"{report.stock_name}_{report.date}.pdf")
                local_path = await download_pdf(
                    report.pdf_url,
                    output_dir=output_dir,
                    filename=safe_filename
                )
                report_dict["local_path"] = local_path
            
            all_reports.append(report_dict)
        
        # Rate limiting
        await asyncio.sleep(1)
    
    logger.info(f"Collected total {len(all_reports)} reports")
    return all_reports


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        # 최신 리포트 5개 수집 (다운로드 없이)
        reports = await collect_reports(pages=1, download=False)
        
        print(f"\n=== Collected {len(reports)} reports ===")
        for r in reports[:5]:
            print(f"- {r['stock_name']}: {r['title']} ({r['broker']}, {r['date']})")
    
    asyncio.run(main())
