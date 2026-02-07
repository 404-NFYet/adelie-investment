"""
PostgreSQL 데이터 로더
- 수집된 데이터를 DB에 저장
- 중복 체크
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)


class DBLoader:
    """PostgreSQL 데이터 로더"""
    
    def __init__(self, dsn: Optional[str] = None):
        """
        Args:
            dsn: PostgreSQL 연결 문자열
        """
        self.dsn = dsn or os.getenv(
            "DATABASE_URL",
            "postgresql://narative:password@localhost:5432/narative"
        )
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """DB 연결 풀 생성"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
            logger.info("Connected to PostgreSQL")
    
    async def close(self) -> None:
        """DB 연결 풀 종료"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def ensure_tables(self) -> None:
        """필요한 테이블 생성"""
        async with self.pool.acquire() as conn:
            # 주식 데이터 테이블
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_daily_movers (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    ticker VARCHAR(10) NOT NULL,
                    name VARCHAR(100),
                    open_price NUMERIC,
                    high_price NUMERIC,
                    low_price NUMERIC,
                    close_price NUMERIC,
                    volume BIGINT,
                    change_pct NUMERIC,
                    mover_type VARCHAR(20) NOT NULL,  -- 'gainer', 'loser', 'high_volume'
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(date, ticker, mover_type)
                )
            """)
            
            # 리서치 리포트 테이블
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS research_reports (
                    id SERIAL PRIMARY KEY,
                    stock_name VARCHAR(100) NOT NULL,
                    stock_code VARCHAR(10),
                    title VARCHAR(500) NOT NULL,
                    broker VARCHAR(100),
                    report_date DATE,
                    pdf_url TEXT,
                    local_path TEXT,
                    target_price VARCHAR(50),
                    opinion VARCHAR(50),
                    extracted_text TEXT,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(stock_code, title, report_date)
                )
            """)
            
            # 시장 요약 테이블
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_summary (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    kospi_open NUMERIC,
                    kospi_high NUMERIC,
                    kospi_low NUMERIC,
                    kospi_close NUMERIC,
                    kospi_volume BIGINT,
                    kosdaq_open NUMERIC,
                    kosdaq_high NUMERIC,
                    kosdaq_low NUMERIC,
                    kosdaq_close NUMERIC,
                    kosdaq_volume BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            logger.info("Tables ensured")
    
    async def save_movers(self, data: dict, mover_type: str) -> int:
        """
        급등/급락/거래량 상위 종목 저장
        
        Args:
            data: get_top_movers() 또는 get_high_volume_stocks() 결과
            mover_type: 'gainer', 'loser', 'high_volume'
            
        Returns:
            int: 저장된 레코드 수
        """
        date_str = data.get("date", "")
        if not date_str:
            logger.warning("No date in data")
            return 0
        
        # 날짜 파싱
        date = datetime.strptime(date_str, "%Y%m%d").date()
        
        # 데이터 추출
        if mover_type == "gainer":
            stocks = data.get("gainers", [])
        elif mover_type == "loser":
            stocks = data.get("losers", [])
        elif mover_type == "high_volume":
            stocks = data.get("high_volume", [])
        else:
            logger.warning(f"Unknown mover_type: {mover_type}")
            return 0
        
        if not stocks:
            return 0
        
        saved = 0
        async with self.pool.acquire() as conn:
            for stock in stocks:
                try:
                    await conn.execute("""
                        INSERT INTO stock_daily_movers 
                        (date, ticker, name, open_price, high_price, low_price, 
                         close_price, volume, change_pct, mover_type)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT (date, ticker, mover_type) 
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume,
                            change_pct = EXCLUDED.change_pct
                    """,
                        date,
                        stock.get("ticker"),
                        stock.get("name"),
                        stock.get("시가"),
                        stock.get("고가"),
                        stock.get("저가"),
                        stock.get("종가"),
                        stock.get("거래량"),
                        stock.get("등락률"),
                        mover_type
                    )
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to save stock {stock.get('ticker')}: {e}")
        
        logger.info(f"Saved {saved} {mover_type} records for {date}")
        return saved
    
    async def save_report(self, report: dict) -> bool:
        """
        리서치 리포트 저장
        
        Args:
            report: 리포트 데이터
            
        Returns:
            bool: 성공 여부
        """
        # 날짜 파싱
        report_date = None
        date_str = report.get("date", "")
        if date_str:
            try:
                # 다양한 형식 처리
                for fmt in ["%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"]:
                    try:
                        report_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO research_reports 
                    (stock_name, stock_code, title, broker, report_date,
                     pdf_url, local_path, target_price, opinion)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (stock_code, title, report_date) 
                    DO UPDATE SET
                        pdf_url = EXCLUDED.pdf_url,
                        local_path = EXCLUDED.local_path,
                        target_price = EXCLUDED.target_price,
                        opinion = EXCLUDED.opinion
                """,
                    report.get("stock_name"),
                    report.get("stock_code"),
                    report.get("title"),
                    report.get("broker"),
                    report_date,
                    report.get("pdf_url"),
                    report.get("local_path"),
                    report.get("target_price"),
                    report.get("opinion")
                )
                logger.debug(f"Saved report: {report.get('title')}")
                return True
            except Exception as e:
                logger.error(f"Failed to save report: {e}")
                return False
    
    async def save_reports(self, reports: list[dict]) -> int:
        """
        여러 리포트 저장
        
        Args:
            reports: 리포트 리스트
            
        Returns:
            int: 저장된 레코드 수
        """
        saved = 0
        for report in reports:
            if await self.save_report(report):
                saved += 1
        
        logger.info(f"Saved {saved}/{len(reports)} reports")
        return saved
    
    async def save_market_summary(self, data: dict) -> bool:
        """
        시장 요약 저장
        
        Args:
            data: get_market_summary() 결과
            
        Returns:
            bool: 성공 여부
        """
        date_str = data.get("date", "")
        if not date_str:
            return False
        
        date = datetime.strptime(date_str, "%Y%m%d").date()
        kospi = data.get("kospi") or {}
        kosdaq = data.get("kosdaq") or {}
        
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO market_summary 
                    (date, kospi_open, kospi_high, kospi_low, kospi_close, kospi_volume,
                     kosdaq_open, kosdaq_high, kosdaq_low, kosdaq_close, kosdaq_volume)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (date) 
                    DO UPDATE SET
                        kospi_open = EXCLUDED.kospi_open,
                        kospi_high = EXCLUDED.kospi_high,
                        kospi_low = EXCLUDED.kospi_low,
                        kospi_close = EXCLUDED.kospi_close,
                        kospi_volume = EXCLUDED.kospi_volume,
                        kosdaq_open = EXCLUDED.kosdaq_open,
                        kosdaq_high = EXCLUDED.kosdaq_high,
                        kosdaq_low = EXCLUDED.kosdaq_low,
                        kosdaq_close = EXCLUDED.kosdaq_close,
                        kosdaq_volume = EXCLUDED.kosdaq_volume
                """,
                    date,
                    kospi.get("open"),
                    kospi.get("high"),
                    kospi.get("low"),
                    kospi.get("close"),
                    kospi.get("volume"),
                    kosdaq.get("open"),
                    kosdaq.get("high"),
                    kosdaq.get("low"),
                    kosdaq.get("close"),
                    kosdaq.get("volume")
                )
                logger.info(f"Saved market summary for {date}")
                return True
            except Exception as e:
                logger.error(f"Failed to save market summary: {e}")
                return False
    
    async def check_exists(self, table: str, date: str) -> bool:
        """
        특정 날짜 데이터 존재 여부 확인
        
        Args:
            table: 테이블명
            date: 날짜 (YYYYMMDD 또는 YYYY-MM-DD)
            
        Returns:
            bool: 존재 여부
        """
        date_str = date.replace("-", "")
        date_obj = datetime.strptime(date_str, "%Y%m%d").date()
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT EXISTS(SELECT 1 FROM {table} WHERE date = $1)",
                date_obj
            )
            return result


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        async with DBLoader() as loader:
            # 테이블 생성
            await loader.ensure_tables()
            print("Tables created/verified")
            
            # 중복 체크 테스트
            exists = await loader.check_exists("stock_daily_movers", "20260205")
            print(f"Data exists for 20260205: {exists}")
    
    asyncio.run(main())
