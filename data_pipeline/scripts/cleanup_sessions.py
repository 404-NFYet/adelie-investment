#!/usr/bin/env python3
"""
24시간 이상 비활성 튜터 세션 정리.
cron: 0 4 * * * python3 cleanup_sessions.py
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import create_engine, text


def cleanup():
    db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # 1. 만료된 세션 종료 처리
        result = conn.execute(text("""
            UPDATE tutor_sessions 
            SET ended_at = NOW() 
            WHERE ended_at IS NULL 
              AND started_at < NOW() - INTERVAL '24 hours'
        """))
        expired = result.rowcount
        print(f"Expired sessions closed: {expired}")

        # 2. LangGraph checkpoint 정리 (테이블 존재 시)
        try:
            result2 = conn.execute(text("""
                DELETE FROM checkpoints 
                WHERE thread_ts < NOW() - INTERVAL '24 hours'
            """))
            cleaned = result2.rowcount
            print(f"Checkpoints cleaned: {cleaned}")
        except Exception:
            print("Checkpoint table not found or empty. Skipping.")

        conn.commit()
    print("Cleanup done.")


if __name__ == "__main__":
    cleanup()
