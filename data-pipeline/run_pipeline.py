#!/usr/bin/env python
"""
데이터 파이프라인 수동 실행 스크립트

사용법:
    python run_pipeline.py --date 2026-02-05 --collect-stocks
    python run_pipeline.py --date 2026-02-05 --collect-reports --pages 2
    python run_pipeline.py --date 2026-02-05 --all
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 환경변수 로드
from dotenv import load_dotenv

# .env 파일 경로 설정
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# 모듈 import
from collectors.stock_collector import (
    get_top_movers,
    get_high_volume_stocks,
    get_market_summary
)
from collectors.naver_report_crawler import collect_reports
from loaders.db_loader import DBLoader

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def run_stock_collection(date: str, top_n: int, save_to_db: bool) -> dict:
    """
    주식 데이터 수집 실행
    
    Args:
        date: 수집 날짜
        top_n: 상위 N개 종목
        save_to_db: DB 저장 여부
        
    Returns:
        dict: 수집 결과
    """
    logger.info(f"Starting stock collection for {date}")
    
    results = {
        "movers": None,
        "high_volume": None,
        "market_summary": None,
        "saved_to_db": False
    }
    
    try:
        # 급등/급락 종목 수집
        logger.info("Collecting top movers...")
        movers = get_top_movers(date, top_n=top_n)
        results["movers"] = movers
        logger.info(f"  Gainers: {len(movers.get('gainers', []))}")
        logger.info(f"  Losers: {len(movers.get('losers', []))}")
        
        # 거래량 상위 종목 수집
        logger.info("Collecting high volume stocks...")
        high_volume = get_high_volume_stocks(date, top_n=top_n)
        results["high_volume"] = high_volume
        logger.info(f"  High volume: {len(high_volume.get('high_volume', []))}")
        
        # 시장 요약 수집
        logger.info("Collecting market summary...")
        market_summary = get_market_summary(date)
        results["market_summary"] = market_summary
        
        # DB 저장
        if save_to_db:
            logger.info("Saving to database...")
            async with DBLoader() as loader:
                await loader.ensure_tables()
                
                await loader.save_movers(movers, "gainer")
                await loader.save_movers(movers, "loser")
                await loader.save_movers(high_volume, "high_volume")
                await loader.save_market_summary(market_summary)
                
                results["saved_to_db"] = True
            logger.info("Saved to database")
        
        logger.info("Stock collection completed")
        
    except Exception as e:
        logger.error(f"Stock collection failed: {e}")
        raise
    
    return results


async def run_report_collection(
    pages: int,
    stock_code: str | None,
    download: bool,
    save_to_db: bool
) -> dict:
    """
    리서치 리포트 수집 실행
    
    Args:
        pages: 수집할 페이지 수
        stock_code: 종목 코드 필터 (선택)
        download: PDF 다운로드 여부
        save_to_db: DB 저장 여부
        
    Returns:
        dict: 수집 결과
    """
    logger.info(f"Starting report collection (pages={pages}, download={download})")
    
    results = {
        "reports": [],
        "total": 0,
        "saved_to_db": False
    }
    
    try:
        # 리포트 수집
        output_dir = Path(__file__).parent / "downloads"
        reports = await collect_reports(
            pages=pages,
            stock_code=stock_code,
            download=download,
            output_dir=str(output_dir)
        )
        
        results["reports"] = reports
        results["total"] = len(reports)
        logger.info(f"Collected {len(reports)} reports")
        
        # DB 저장
        if save_to_db and reports:
            logger.info("Saving reports to database...")
            async with DBLoader() as loader:
                await loader.ensure_tables()
                saved = await loader.save_reports(reports)
                results["saved_to_db"] = True
                logger.info(f"Saved {saved} reports to database")
        
        logger.info("Report collection completed")
        
    except Exception as e:
        logger.error(f"Report collection failed: {e}")
        raise
    
    return results


async def run_pdf_processing(pdf_path: str, max_pages: int | None) -> dict:
    """
    PDF 처리 실행
    
    Args:
        pdf_path: PDF 파일 경로
        max_pages: 최대 처리 페이지 수
        
    Returns:
        dict: 처리 결과
    """
    from processors.pdf_processor import process_pdf
    
    logger.info(f"Processing PDF: {pdf_path}")
    
    try:
        result = await process_pdf(pdf_path, max_pages=max_pages)
        logger.info(f"Processed {result['total_pages']} pages")
        return result
        
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise


def print_summary(results: dict) -> None:
    """결과 요약 출력"""
    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    
    if "stocks" in results:
        stocks = results["stocks"]
        print("\n[Stock Collection]")
        if stocks.get("movers"):
            print(f"  Gainers: {len(stocks['movers'].get('gainers', []))}")
            print(f"  Losers: {len(stocks['movers'].get('losers', []))}")
        if stocks.get("high_volume"):
            print(f"  High Volume: {len(stocks['high_volume'].get('high_volume', []))}")
        if stocks.get("market_summary"):
            ms = stocks["market_summary"]
            if ms.get("kospi"):
                print(f"  KOSPI: {ms['kospi'].get('close')}")
            if ms.get("kosdaq"):
                print(f"  KOSDAQ: {ms['kosdaq'].get('close')}")
        print(f"  Saved to DB: {stocks.get('saved_to_db', False)}")
    
    if "reports" in results:
        reports = results["reports"]
        print("\n[Report Collection]")
        print(f"  Total reports: {reports.get('total', 0)}")
        print(f"  Saved to DB: {reports.get('saved_to_db', False)}")
    
    if "pdf" in results:
        pdf = results["pdf"]
        print("\n[PDF Processing]")
        print(f"  File: {pdf.get('file', 'N/A')}")
        print(f"  Pages: {pdf.get('total_pages', 0)}")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Narrative Investment Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 특정 날짜 주식 데이터 수집
  python run_pipeline.py --date 2026-02-05 --collect-stocks
  
  # 리서치 리포트 수집 (2페이지, PDF 다운로드)
  python run_pipeline.py --collect-reports --pages 2 --download-pdf
  
  # 특정 종목 리포트만 수집
  python run_pipeline.py --collect-reports --stock-code 005930 --pages 3
  
  # 모든 수집 실행 (DB 저장)
  python run_pipeline.py --date 2026-02-05 --all --save-to-db
  
  # PDF 처리 (Vision API)
  python run_pipeline.py --process-pdf ./downloads/report.pdf --max-pages 5
        """
    )
    
    # 날짜 옵션
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="수집 날짜 (기본: 오늘, 형식: YYYY-MM-DD)"
    )
    
    # 수집 옵션
    parser.add_argument(
        "--collect-stocks",
        action="store_true",
        help="주식 데이터 수집 (급등/급락, 거래량 상위)"
    )
    parser.add_argument(
        "--collect-reports",
        action="store_true",
        help="네이버 리서치 리포트 수집"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="모든 수집 실행"
    )
    
    # 주식 수집 옵션
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="상위 N개 종목 (기본: 10)"
    )
    
    # 리포트 수집 옵션
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="리포트 수집 페이지 수 (기본: 1)"
    )
    parser.add_argument(
        "--stock-code",
        type=str,
        default=None,
        help="특정 종목 코드로 필터 (예: 005930)"
    )
    parser.add_argument(
        "--download-pdf",
        action="store_true",
        help="리포트 PDF 다운로드"
    )
    
    # PDF 처리 옵션
    parser.add_argument(
        "--process-pdf",
        type=str,
        default=None,
        help="처리할 PDF 파일 경로"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="PDF 최대 처리 페이지 수"
    )
    
    # 저장 옵션
    parser.add_argument(
        "--save-to-db",
        action="store_true",
        help="결과를 PostgreSQL에 저장"
    )
    
    # 기타
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 로그 출력"
    )
    
    args = parser.parse_args()
    
    # 로그 레벨 설정
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 최소 하나의 작업 필요
    if not any([args.collect_stocks, args.collect_reports, args.all, args.process_pdf]):
        parser.print_help()
        print("\nError: At least one action is required (--collect-stocks, --collect-reports, --all, or --process-pdf)")
        sys.exit(1)
    
    # 비동기 실행
    async def run():
        results = {}
        
        try:
            # 주식 데이터 수집
            if args.collect_stocks or args.all:
                results["stocks"] = await run_stock_collection(
                    date=args.date,
                    top_n=args.top_n,
                    save_to_db=args.save_to_db
                )
            
            # 리포트 수집
            if args.collect_reports or args.all:
                results["reports"] = await run_report_collection(
                    pages=args.pages,
                    stock_code=args.stock_code,
                    download=args.download_pdf,
                    save_to_db=args.save_to_db
                )
            
            # PDF 처리
            if args.process_pdf:
                results["pdf"] = await run_pdf_processing(
                    pdf_path=args.process_pdf,
                    max_pages=args.max_pages
                )
            
            # 결과 요약
            print_summary(results)
            
        except KeyboardInterrupt:
            logger.warning("Pipeline interrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            sys.exit(1)
    
    asyncio.run(run())


if __name__ == "__main__":
    main()
