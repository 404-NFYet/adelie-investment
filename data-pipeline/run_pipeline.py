#!/usr/bin/env python3
"""
Narrative Investment - Data Pipeline Runner

통합 데이터 파이프라인 실행 스크립트.
주식 데이터 수집, 리포트 크롤링, PDF 추출, 그래프 DB 적재를 수행합니다.

사용법:
    python run_pipeline.py --all          # 모든 파이프라인 실행
    python run_pipeline.py --stock        # 주식 데이터만
    python run_pipeline.py --report       # 리포트 크롤링만
    python run_pipeline.py --vision       # PDF Vision 추출만
    python run_pipeline.py --neo4j        # Neo4j 적재만
    python run_pipeline.py --date 20260205  # 특정 날짜
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


class PipelineRunner:
    """통합 파이프라인 실행기"""
    
    def __init__(self, date: str = None):
        """
        Args:
            date: Target date in YYYYMMDD format (defaults to today)
        """
        self.date = date or datetime.now().strftime("%Y%m%d")
        self.results = {}
        
        print("=" * 60)
        print(f"🚀 Narrative Investment Pipeline Runner")
        print(f"📅 Target Date: {self.date}")
        print("=" * 60)
    
    def run_stock_collection(self) -> dict:
        """주식 데이터 수집 (급등/급락/거래량)"""
        print("\n" + "-" * 40)
        print("📈 Phase 1: Stock Data Collection")
        print("-" * 40)
        
        result = {
            "task": "stock_collection",
            "status": "pending",
            "data": {},
        }
        
        try:
            from collectors.stock_collector import (
                get_top_movers,
                get_high_volume_stocks,
                get_market_summary,
            )
            
            start_time = time.time()
            
            # Get top movers
            print("  📊 Fetching top movers...")
            movers = get_top_movers(self.date, top_n=10)
            
            # Get high volume stocks
            print("  📊 Fetching high volume stocks...")
            volume = get_high_volume_stocks(self.date, top_n=10)
            
            # Get market summary
            print("  📊 Fetching market summary...")
            market = get_market_summary(self.date)
            
            elapsed = time.time() - start_time
            
            result["status"] = "success"
            result["data"] = {
                "gainers_count": len(movers.get("gainers", [])),
                "losers_count": len(movers.get("losers", [])),
                "high_volume_count": len(volume.get("high_volume", [])),
                "market_summary": market,
            }
            result["duration_seconds"] = elapsed
            
            print(f"  ✅ Collected {result['data']['gainers_count']} gainers, {result['data']['losers_count']} losers")
            print(f"  ⏱️ Duration: {elapsed:.2f}s")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
        
        self.results["stock"] = result
        return result
    
    async def run_report_collection(self, pages: int = 2, download: bool = True) -> dict:
        """네이버 리포트 크롤링"""
        print("\n" + "-" * 40)
        print("📰 Phase 2: Report Collection")
        print("-" * 40)
        
        result = {
            "task": "report_collection",
            "status": "pending",
            "data": {},
        }
        
        try:
            from collectors.naver_report_crawler import collect_reports
            
            start_time = time.time()
            
            print(f"  📄 Crawling {pages} pages of reports...")
            reports = await collect_reports(pages=pages, download=download)
            
            elapsed = time.time() - start_time
            
            result["status"] = "success"
            result["data"] = {
                "reports_count": len(reports),
                "reports": reports[:5],  # Sample
            }
            result["duration_seconds"] = elapsed
            
            print(f"  ✅ Collected {len(reports)} reports")
            print(f"  ⏱️ Duration: {elapsed:.2f}s")
            
            # Upload to MinIO if enabled
            if download and reports:
                await self._upload_reports_to_minio(reports)
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
        
        self.results["report"] = result
        return result
    
    async def _upload_reports_to_minio(self, reports: list):
        """리포트 PDF를 MinIO에 업로드"""
        try:
            from services.minio_service import get_minio_service
            
            minio = get_minio_service()
            uploaded = 0
            
            for report in reports:
                if "pdf_path" in report and os.path.exists(report["pdf_path"]):
                    try:
                        object_name = minio.upload_pdf(report["pdf_path"])
                        report["minio_path"] = object_name
                        uploaded += 1
                    except Exception as e:
                        print(f"    ⚠️ Upload failed for {report.get('title', 'unknown')}: {e}")
            
            print(f"  📤 Uploaded {uploaded}/{len(reports)} PDFs to MinIO")
            
        except Exception as e:
            print(f"  ⚠️ MinIO upload skipped: {e}")
    
    async def run_vision_extraction(self, limit: int = 5) -> dict:
        """Vision API로 PDF 데이터 추출"""
        print("\n" + "-" * 40)
        print("👁️ Phase 3: Vision API Extraction")
        print("-" * 40)
        
        result = {
            "task": "vision_extraction",
            "status": "pending",
            "data": {},
        }
        
        try:
            from services.vision_extractor import get_vision_extractor
            from services.minio_service import get_minio_service
            
            extractor = get_vision_extractor()
            
            start_time = time.time()
            extractions = []
            
            # Try to get PDFs from MinIO
            try:
                minio = get_minio_service()
                pdfs = minio.list_pdfs(prefix=self.date[:6])  # Month prefix
                
                print(f"  📑 Found {len(pdfs)} PDFs in MinIO")
                
                for pdf_info in pdfs[:limit]:
                    print(f"    Processing: {pdf_info['name']}...")
                    
                    pdf_data = minio.download_pdf(pdf_info["name"])
                    extraction = extractor.extract_from_pdf(pdf_data, max_pages=3)
                    
                    extractions.append({
                        "pdf_name": pdf_info["name"],
                        "summary": extraction.get("summary", {}),
                    })
                    
            except Exception as e:
                print(f"  ⚠️ MinIO not available: {e}")
                
                # Try local PDFs
                local_pdf_dir = PROJECT_ROOT / "data-pipeline" / "downloads"
                if local_pdf_dir.exists():
                    pdfs = list(local_pdf_dir.glob("*.pdf"))[:limit]
                    
                    for pdf_path in pdfs:
                        print(f"    Processing: {pdf_path.name}...")
                        
                        with open(pdf_path, "rb") as f:
                            pdf_data = f.read()
                        
                        extraction = extractor.extract_from_pdf(pdf_data, max_pages=3)
                        
                        extractions.append({
                            "pdf_name": pdf_path.name,
                            "summary": extraction.get("summary", {}),
                        })
            
            elapsed = time.time() - start_time
            
            result["status"] = "success"
            result["data"] = {
                "extractions_count": len(extractions),
                "extractions": extractions,
            }
            result["duration_seconds"] = elapsed
            
            print(f"  ✅ Extracted data from {len(extractions)} PDFs")
            print(f"  ⏱️ Duration: {elapsed:.2f}s")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
        
        self.results["vision"] = result
        return result
    
    def run_neo4j_loading(self) -> dict:
        """Neo4j에 기업 관계 데이터 적재"""
        print("\n" + "-" * 40)
        print("🔗 Phase 4: Neo4j Graph Loading")
        print("-" * 40)
        
        result = {
            "task": "neo4j_loading",
            "status": "pending",
            "data": {},
        }
        
        try:
            from services.neo4j_service import get_neo4j_service
            
            neo4j = get_neo4j_service()
            
            if not neo4j.verify_connectivity():
                raise ConnectionError("Neo4j connection failed")
            
            start_time = time.time()
            
            # Initialize schema
            print("  📐 Initializing schema...")
            neo4j.init_schema()
            
            # Load companies from stock collection results
            if "stock" in self.results and self.results["stock"]["status"] == "success":
                print("  📥 Loading companies from stock data...")
                
                # TODO: 실제 운영에서는 수집된 stock 데이터에서 기업 목록을 추출해야 함.
                #       현재는 하드코딩된 샘플 데이터를 사용하고 있으므로,
                #       self.results["stock"]["data"]에서 동적으로 로드하도록 개선 필요.
                sample_companies = [
                    {"stock_code": "005930", "name": "삼성전자", "market": "KOSPI"},
                    {"stock_code": "000660", "name": "SK하이닉스", "market": "KOSPI"},
                    {"stock_code": "035420", "name": "NAVER", "market": "KOSPI"},
                    {"stock_code": "035720", "name": "카카오", "market": "KOSPI"},
                    {"stock_code": "051910", "name": "LG화학", "market": "KOSPI"},
                ]
                
                count = neo4j.bulk_create_companies(sample_companies)
                print(f"    Created {count} company nodes")
                
                # TODO: 관계 데이터도 하드코딩 → 수집된 데이터 기반으로 변경 필요
                sample_relationships = [
                    {"supplier_code": "000660", "customer_code": "005930", "product": "메모리 반도체", "confidence": 0.95},
                    {"supplier_code": "051910", "customer_code": "005930", "product": "배터리", "confidence": 0.8},
                ]
                
                rel_count = neo4j.bulk_create_relationships(sample_relationships)
                print(f"    Created {rel_count} relationships")
            
            # Get stats
            stats = neo4j.get_graph_stats()
            
            elapsed = time.time() - start_time
            
            result["status"] = "success"
            result["data"] = {
                "graph_stats": stats,
            }
            result["duration_seconds"] = elapsed
            
            print(f"  ✅ Neo4j loading complete")
            print(f"  📊 Stats: {stats}")
            print(f"  ⏱️ Duration: {elapsed:.2f}s")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
        
        self.results["neo4j"] = result
        return result
    
    def save_briefing_to_db(self) -> dict:
        """브리핑 데이터를 PostgreSQL에 저장"""
        print("\n" + "-" * 40)
        print("💾 Phase 5: Save Briefing to Database")
        print("-" * 40)
        
        result = {
            "task": "save_briefing",
            "status": "pending",
        }
        
        try:
            if "stock" not in self.results or self.results["stock"]["status"] != "success":
                raise ValueError("Stock collection must succeed first")
            
            from sqlalchemy import create_engine, text
            
            database_url = os.getenv("DATABASE_URL", "")
            if not database_url:
                raise ValueError("DATABASE_URL not set")
            
            # Use sync driver
            if "+asyncpg" in database_url:
                database_url = database_url.replace("+asyncpg", "")
            
            engine = create_engine(database_url)
            
            start_time = time.time()
            
            # Insert briefing
            with engine.connect() as conn:
                # Check if briefing exists
                check_sql = text("""
                    SELECT id FROM daily_briefings WHERE briefing_date = :date
                """)
                existing = conn.execute(check_sql, {"date": self.date}).fetchone()
                
                if existing:
                    print(f"  ℹ️ Briefing for {self.date} already exists")
                    result["status"] = "skipped"
                    return result
                
                # Insert new briefing
                insert_sql = text("""
                    INSERT INTO daily_briefings (briefing_date, market_summary, top_keywords)
                    VALUES (:date, :summary, :keywords)
                    RETURNING id
                """)
                
                stock_data = self.results["stock"]["data"]
                market = stock_data.get("market_summary", {})
                
                summary = f"KOSPI {market.get('kospi', {}).get('close', '-')}, KOSDAQ {market.get('kosdaq', {}).get('close', '-')}"
                
                result_row = conn.execute(insert_sql, {
                    "date": self.date,
                    "summary": summary,
                    "keywords": json.dumps({"keywords": []}),
                }).fetchone()
                
                briefing_id = result_row[0]
                print(f"  📝 Created briefing ID: {briefing_id}")
                
                conn.commit()
            
            elapsed = time.time() - start_time
            
            result["status"] = "success"
            result["duration_seconds"] = elapsed
            
            print(f"  ✅ Briefing saved")
            print(f"  ⏱️ Duration: {elapsed:.2f}s")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
        
        self.results["save_briefing"] = result
        return result
    
    async def run_all(self):
        """모든 파이프라인 실행"""
        total_start = time.time()
        
        # Phase 1: Stock Collection
        self.run_stock_collection()
        
        # Phase 2: Report Collection
        await self.run_report_collection()
        
        # Phase 3: Vision Extraction
        await self.run_vision_extraction()
        
        # Phase 4: Neo4j Loading
        self.run_neo4j_loading()
        
        # Phase 5: Save to DB
        self.save_briefing_to_db()
        
        total_elapsed = time.time() - total_start
        
        # Print summary
        print("\n" + "=" * 60)
        print("📋 Pipeline Summary")
        print("=" * 60)
        
        for task, result in self.results.items():
            status_emoji = "✅" if result["status"] == "success" else "❌" if result["status"] == "failed" else "⏭️"
            duration = result.get("duration_seconds", 0)
            print(f"  {status_emoji} {task}: {result['status']} ({duration:.2f}s)")
        
        print("-" * 60)
        print(f"  ⏱️ Total Duration: {total_elapsed:.2f}s")
        print("=" * 60)
        
        return self.results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Narrative Investment Data Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_pipeline.py --all
    python run_pipeline.py --stock --date 20260205
    python run_pipeline.py --report --pages 3
    python run_pipeline.py --vision --limit 10
        """,
    )
    
    parser.add_argument("--all", action="store_true", help="Run all pipeline steps")
    parser.add_argument("--stock", action="store_true", help="Run stock data collection")
    parser.add_argument("--report", action="store_true", help="Run report collection")
    parser.add_argument("--vision", action="store_true", help="Run Vision API extraction")
    parser.add_argument("--neo4j", action="store_true", help="Run Neo4j loading")
    parser.add_argument("--date", type=str, help="Target date (YYYYMMDD)")
    parser.add_argument("--pages", type=int, default=2, help="Report pages to crawl")
    parser.add_argument("--limit", type=int, default=5, help="Vision extraction limit")
    parser.add_argument("--no-download", action="store_true", help="Skip PDF download")
    
    args = parser.parse_args()
    
    # If no specific task, default to --all
    if not any([args.all, args.stock, args.report, args.vision, args.neo4j]):
        args.all = True
    
    runner = PipelineRunner(date=args.date)
    
    async def run():
        if args.all:
            await runner.run_all()
        else:
            if args.stock:
                runner.run_stock_collection()
            
            if args.report:
                await runner.run_report_collection(
                    pages=args.pages,
                    download=not args.no_download,
                )
            
            if args.vision:
                await runner.run_vision_extraction(limit=args.limit)
            
            if args.neo4j:
                runner.run_neo4j_loading()
    
    asyncio.run(run())
    
    # Exit with error if any task failed
    failed = any(r["status"] == "failed" for r in runner.results.values())
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
