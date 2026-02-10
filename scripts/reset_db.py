"""
DB 초기화 스크립트 - Phase 1-3

기존 컨텐츠 데이터를 TRUNCATE하고,
모든 유저의 포트폴리오를 100만원 기본값으로 초기화합니다.

사용법:
    python scripts/reset_db.py              # 실행 (확인 프롬프트 포함)
    python scripts/reset_db.py --force      # 확인 없이 강제 실행
    python scripts/reset_db.py --dry-run    # 실행 없이 미리보기
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend_api"))

from sqlalchemy import text
from app.core.database import engine


# TRUNCATE 대상 테이블 (순서 중요: FK 의존성 고려)
CONTENT_TABLES = [
    "tutor_messages",       # FK -> tutor_sessions
    "tutor_sessions",
    "notifications",
    "briefing_rewards",
    "dwell_rewards",
    "case_stock_relations", # FK -> historical_cases
    "case_matches",         # FK -> historical_cases
    "historical_cases",
    "briefing_stocks",      # FK -> daily_briefings
    "daily_briefings",
    "broker_reports",
    "company_relations",    # Neo4j 캐시 테이블 (DROP 예정)
    "learning_progress",
]

# 모의투자 테이블
TRADING_TABLES = [
    "simulation_trades",    # FK -> user_portfolios
    "portfolio_holdings",   # FK -> user_portfolios
]

# 초기 자금 (100만원)
INITIAL_CASH = 1_000_000


async def reset_database(dry_run: bool = False):
    """DB 초기화 실행"""
    
    async with engine.begin() as conn:
        # 1. 현재 상태 확인
        print("\n" + "=" * 50)
        print("📊 현재 DB 상태")
        print("=" * 50)
        
        for table in CONTENT_TABLES + TRADING_TABLES:
            try:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  {table}: {count:,}건")
            except Exception:
                print(f"  {table}: (테이블 없음)")
        
        # 유저/포트폴리오 상태
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"\n  👤 전체 유저 수: {user_count}명")
            
            result = await conn.execute(text(
                "SELECT COUNT(*), AVG(current_cash), MIN(current_cash), MAX(current_cash) "
                "FROM user_portfolios"
            ))
            row = result.one()
            print(f"  💰 포트폴리오 수: {row[0]}개")
            if row[1]:
                print(f"     평균 잔고: {row[1]:,.0f}원")
                print(f"     최소 잔고: {row[2]:,.0f}원")
                print(f"     최대 잔고: {row[3]:,.0f}원")
        except Exception as e:
            print(f"  ⚠️ 유저/포트폴리오 조회 실패: {e}")
        
        if dry_run:
            print("\n🔍 [DRY RUN] 실제 실행하지 않습니다.")
            return
        
        # 2. 컨텐츠 데이터 TRUNCATE
        print("\n" + "=" * 50)
        print("🗑️ 컨텐츠 데이터 TRUNCATE")
        print("=" * 50)
        
        for table in CONTENT_TABLES:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                print(f"  ✅ {table} TRUNCATED")
            except Exception as e:
                print(f"  ⚠️ {table}: {e}")
        
        # 3. 모의투자 데이터 TRUNCATE
        print("\n" + "=" * 50)
        print("🗑️ 모의투자 데이터 TRUNCATE")
        print("=" * 50)
        
        for table in TRADING_TABLES:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                print(f"  ✅ {table} TRUNCATED")
            except Exception as e:
                print(f"  ⚠️ {table}: {e}")
        
        # 4. 포트폴리오 100만원 초기화
        print("\n" + "=" * 50)
        print(f"💰 포트폴리오 초기화 ({INITIAL_CASH:,}원)")
        print("=" * 50)
        
        try:
            result = await conn.execute(text(
                f"UPDATE user_portfolios "
                f"SET current_cash = {INITIAL_CASH}, "
                f"    initial_cash = {INITIAL_CASH}, "
                f"    total_profit = 0, "
                f"    total_profit_rate = 0, "
                f"    updated_at = NOW()"
            ))
            print(f"  ✅ {result.rowcount}개 포트폴리오 초기화 완료")
        except Exception as e:
            print(f"  ⚠️ 포트폴리오 초기화 실패: {e}")
        
        # 5. 최종 확인
        print("\n" + "=" * 50)
        print("✅ DB 초기화 완료")
        print("=" * 50)
        
        # 초기화 후 상태
        for table in CONTENT_TABLES + TRADING_TABLES:
            try:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                if count > 0:
                    print(f"  ⚠️ {table}: {count:,}건 남아있음")
            except Exception:
                pass
        
        try:
            result = await conn.execute(text(
                "SELECT COUNT(*), AVG(current_cash) FROM user_portfolios"
            ))
            row = result.one()
            print(f"\n  💰 포트폴리오 {row[0]}개: 평균 잔고 {row[1]:,.0f}원")
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="DB 초기화 스크립트")
    parser.add_argument("--force", action="store_true", help="확인 없이 강제 실행")
    parser.add_argument("--dry-run", action="store_true", help="실행 없이 미리보기")
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN 모드 - 현재 상태만 확인합니다.")
        asyncio.run(reset_database(dry_run=True))
        return
    
    if not args.force:
        print("⚠️  경고: 이 스크립트는 모든 컨텐츠 데이터를 삭제하고")
        print("         모든 포트폴리오를 100만원으로 초기화합니다.")
        print("         사용자 계정(users, user_settings)은 유지됩니다.")
        confirm = input("\n정말 실행하시겠습니까? (yes/no): ")
        if confirm.lower() != "yes":
            print("취소되었습니다.")
            return
    
    asyncio.run(reset_database(dry_run=False))


if __name__ == "__main__":
    main()
