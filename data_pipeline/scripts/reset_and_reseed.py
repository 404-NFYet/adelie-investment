#!/usr/bin/env python3
"""
DB 초기화 및 재시딩 스크립트.

지정된 테이블의 데이터를 FK 의존성 순서대로 삭제하고,
신규 테이블(market_daily_history, stock_daily_history)을 생성한다.
용어집(glossary) 데이터는 보존한다.

사용법:
    python3 data_pipeline/scripts/reset_and_reseed.py
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정 (스크립트 기준 ../../)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import psycopg2
from psycopg2 import sql

# ============================================================
# FK 의존성 순서대로 삭제할 테이블 목록
# glossary 관련 테이블은 포함하지 않음
# ============================================================
TABLES_TO_CLEAR = [
    "tutor_messages",        # tutor_sessions FK 참조
    "tutor_sessions",
    "case_stock_relations",  # historical_cases FK 참조
    "case_matches",          # historical_cases FK 참조
    "historical_cases",
    "briefing_stocks",       # daily_briefings FK 참조
    "daily_briefings",
    "learning_progress",
]

# ============================================================
# 신규 생성할 테이블 DDL
# ============================================================
CREATE_MARKET_DAILY_HISTORY = """
CREATE TABLE IF NOT EXISTS market_daily_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    index_code VARCHAR(10) NOT NULL,   -- '1001': KOSPI, '2001': KOSDAQ
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, index_code)
);
"""

CREATE_STOCK_DAILY_HISTORY = """
CREATE TABLE IF NOT EXISTS stock_daily_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    change_pct NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, ticker)
);
"""


def get_connection():
    """환경변수에서 DB 접속 정보를 읽어 psycopg2 연결을 반환한다."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "10.10.10.10"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "narrative_invest"),
        user=os.getenv("DB_USER", "narative"),
        password=os.getenv("DB_PASSWORD", "password"),
    )
    return conn


def print_row_counts(cur, tables):
    """각 테이블의 현재 행 수를 출력한다."""
    print("\n📊 테이블별 행 수:")
    print("-" * 40)
    for table in tables:
        try:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))
            )
            count = cur.fetchone()[0]
            print(f"  {table:<30} {count:>8} rows")
        except psycopg2.errors.UndefinedTable:
            # 테이블이 아직 존재하지 않는 경우
            cur.connection.rollback()
            print(f"  {table:<30} (테이블 없음)")
    print("-" * 40)


def clear_tables(cur):
    """FK 의존성 순서대로 테이블 데이터를 삭제한다."""
    print("\n🗑️  테이블 데이터 삭제 시작...")
    for table in TABLES_TO_CLEAR:
        try:
            cur.execute(
                sql.SQL("DELETE FROM {}").format(sql.Identifier(table))
            )
            deleted = cur.rowcount
            print(f"  ✅ {table}: {deleted}건 삭제")
        except psycopg2.errors.UndefinedTable:
            # 테이블이 존재하지 않으면 건너뛰기
            cur.connection.rollback()
            print(f"  ⏭️  {table}: 테이블이 존재하지 않아 건너뜀")
        except Exception as e:
            cur.connection.rollback()
            print(f"  ❌ {table}: 삭제 실패 - {e}")


def create_new_tables(cur):
    """신규 테이블을 생성한다 (이미 존재하면 무시)."""
    print("\n🏗️  신규 테이블 생성...")

    try:
        cur.execute(CREATE_MARKET_DAILY_HISTORY)
        print("  ✅ market_daily_history 테이블 준비 완료")
    except Exception as e:
        cur.connection.rollback()
        print(f"  ❌ market_daily_history 생성 실패 - {e}")

    try:
        cur.execute(CREATE_STOCK_DAILY_HISTORY)
        print("  ✅ stock_daily_history 테이블 준비 완료")
    except Exception as e:
        cur.connection.rollback()
        print(f"  ❌ stock_daily_history 생성 실패 - {e}")


def confirm_reset():
    """사용자에게 리셋 확인을 요청한다."""
    db_name = os.getenv("DB_NAME", "narrative_invest")
    db_host = os.getenv("DB_HOST", "10.10.10.10")

    print("=" * 55)
    print("⚠️  DB 초기화 스크립트 (Narrative Investment)")
    print("=" * 55)
    print(f"  대상 DB : {db_name} @ {db_host}")
    print(f"  삭제 테이블: {len(TABLES_TO_CLEAR)}개")
    print(f"  보존 테이블: glossary 관련 (삭제하지 않음)")
    print(f"  신규 생성 : market_daily_history, stock_daily_history")
    print("=" * 55)
    print()
    print("삭제 대상 테이블:")
    for i, t in enumerate(TABLES_TO_CLEAR, 1):
        print(f"  {i}. {t}")
    print()

    answer = input("정말 초기화하시겠습니까? (yes 입력): ").strip()
    if answer.lower() != "yes":
        print("취소되었습니다.")
        sys.exit(0)


def main():
    # 1. 확인 프롬프트
    confirm_reset()

    # 2. DB 연결
    print("\n🔌 데이터베이스 연결 중...")
    try:
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()
        print("  연결 성공!")
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        sys.exit(1)

    try:
        # 3. 삭제 전 행 수 확인
        print("\n[삭제 전 상태]")
        print_row_counts(cur, TABLES_TO_CLEAR)

        # 4. 테이블 데이터 삭제
        clear_tables(cur)

        # 5. 신규 테이블 생성
        create_new_tables(cur)

        # 6. 커밋
        conn.commit()
        print("\n✅ 모든 변경사항이 커밋되었습니다.")

        # 7. 삭제 후 행 수 확인 (신규 테이블 포함)
        all_tables = TABLES_TO_CLEAR + ["market_daily_history", "stock_daily_history"]
        print("\n[삭제 후 상태]")
        print_row_counts(cur, all_tables)

        print("\n🎉 DB 초기화 완료!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 오류 발생, 롤백 수행: {e}")
        sys.exit(1)

    finally:
        cur.close()
        conn.close()
        print("🔌 데이터베이스 연결 종료")


if __name__ == "__main__":
    main()
