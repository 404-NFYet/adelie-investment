#!/usr/bin/env python3
"""
Adelie Investment - DB 초기화 스크립트

기존 컨텐츠 데이터를 삭제하고 모든 유저의 포트폴리오를 100만원으로 리셋합니다.

사용법:
    python scripts/reset_db.py                    # 기본 실행 (확인 필요)
    python scripts/reset_db.py --force            # 확인 없이 즉시 실행
    python scripts/reset_db.py --dry-run          # 실행 없이 SQL만 출력
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


# 초기화할 테이블 목록 (컨텐츠 관련)
CONTENT_TABLES = [
    # 브리핑 관련
    "briefing_stocks",
    "daily_briefings",
    
    # 역사적 사례 관련
    "case_stock_relations",
    "case_matches",
    "historical_cases",
    
    # 리포트 관련
    "broker_reports",
    
    # 보상 관련
    "briefing_rewards",
    "dwell_rewards",
    
    # 튜터 세션
    "tutor_messages",
    "tutor_sessions",
    
    # 알림
    "notifications",
    
    # (새 테이블이 추가되면 여기에 추가)
    # "narrative_scenarios",
    # "daily_narratives",
]

# 모의투자 테이블 (거래 기록 삭제)
TRADING_TABLES = [
    "simulation_trades",
    "portfolio_holdings",
]

# 기본 포트폴리오 금액 (100만원)
DEFAULT_CASH = 1_000_000


async def reset_database(dry_run: bool = False):
    """
    데이터베이스 초기화 실행
    
    Args:
        dry_run: True면 SQL만 출력하고 실행하지 않음
    """
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # asyncpg 드라이버 확인
    if "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    engine = create_async_engine(database_url, echo=dry_run)
    
    print("=" * 60)
    print("🔄 Adelie Investment DB 초기화")
    print("=" * 60)
    
    if dry_run:
        print("ℹ️  DRY RUN 모드 - 실제 실행되지 않습니다")
        print()
    
    async with engine.begin() as conn:
        # Step 1: 컨텐츠 테이블 TRUNCATE
        print("\n📦 Step 1: 컨텐츠 데이터 삭제")
        print("-" * 40)
        
        for table in CONTENT_TABLES:
            sql = f"TRUNCATE TABLE {table} CASCADE"
            print(f"  🗑️  {table}")
            
            if not dry_run:
                try:
                    await conn.execute(text(sql))
                except Exception as e:
                    print(f"    ⚠️  스킵됨 (테이블 없음 또는 오류): {e}")
        
        # Step 2: 모의투자 거래 기록 삭제
        print("\n📦 Step 2: 모의투자 거래 기록 삭제")
        print("-" * 40)
        
        for table in TRADING_TABLES:
            sql = f"TRUNCATE TABLE {table} CASCADE"
            print(f"  🗑️  {table}")
            
            if not dry_run:
                try:
                    await conn.execute(text(sql))
                except Exception as e:
                    print(f"    ⚠️  스킵됨 (테이블 없음 또는 오류): {e}")
        
        # Step 3: 모든 유저 포트폴리오를 100만원으로 리셋
        print("\n💰 Step 3: 포트폴리오 100만원 리셋")
        print("-" * 40)
        
        reset_sql = text("""
            UPDATE user_portfolios 
            SET current_cash = :cash,
                initial_cash = :cash,
                total_realized_profit = 0,
                updated_at = NOW()
        """)
        
        print(f"  💵 모든 유저의 current_cash, initial_cash = {DEFAULT_CASH:,}원")
        print(f"  💵 total_realized_profit = 0")
        
        if not dry_run:
            try:
                result = await conn.execute(reset_sql, {"cash": DEFAULT_CASH})
                print(f"  ✅ {result.rowcount}개 포트폴리오 리셋 완료")
            except Exception as e:
                print(f"    ⚠️  오류: {e}")
        
        # Step 4: 통계 출력
        if not dry_run:
            print("\n📊 Step 4: 최종 상태 확인")
            print("-" * 40)
            
            # 포트폴리오 수 확인
            count_result = await conn.execute(text("SELECT COUNT(*) FROM user_portfolios"))
            portfolio_count = count_result.scalar()
            print(f"  📈 총 포트폴리오 수: {portfolio_count}")
            
            # 샘플 확인
            sample_result = await conn.execute(text("""
                SELECT p.id, u.username, p.current_cash, p.initial_cash
                FROM user_portfolios p
                JOIN users u ON p.user_id = u.id
                LIMIT 3
            """))
            
            print(f"  📋 샘플 포트폴리오:")
            for row in sample_result:
                print(f"      - {row.username}: {row.current_cash:,}원")
    
    await engine.dispose()
    
    print("\n" + "=" * 60)
    if dry_run:
        print("✅ DRY RUN 완료 - 실제 변경 없음")
    else:
        print("✅ DB 초기화 완료")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Adelie Investment DB 초기화 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="확인 없이 즉시 실행"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="실행 없이 SQL만 출력"
    )
    
    args = parser.parse_args()
    
    if not args.force and not args.dry_run:
        print("⚠️  경고: 이 스크립트는 모든 컨텐츠 데이터와 거래 기록을 삭제합니다!")
        print("⚠️  모든 유저의 포트폴리오가 100만원으로 초기화됩니다!")
        print()
        confirm = input("계속하시겠습니까? (yes/no): ")
        if confirm.lower() not in ("yes", "y"):
            print("취소되었습니다.")
            sys.exit(0)
    
    asyncio.run(reset_database(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
