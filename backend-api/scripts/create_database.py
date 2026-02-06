#!/usr/bin/env python3
"""
데이터베이스 생성 스크립트
PostgreSQL에 narrative_invest 데이터베이스를 생성합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def create_database():
    """데이터베이스 생성"""
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "narrative_invest")
    
    print(f"🔗 PostgreSQL 연결: {db_host}:{db_port}")
    
    # postgres 데이터베이스에 연결
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    
    # 데이터베이스 존재 확인
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    
    if cursor.fetchone():
        print(f"ℹ️  데이터베이스 '{db_name}'이(가) 이미 존재합니다.")
    else:
        # 데이터베이스 생성
        cursor.execute(f'CREATE DATABASE {db_name}')
        print(f"✅ 데이터베이스 '{db_name}' 생성 완료")
    
    # pgvector extension 설치 시도
    cursor.close()
    conn.close()
    
    # 새 데이터베이스에 연결하여 extension 설치
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        dbname=db_name
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✅ pgvector extension 설치 완료")
    except Exception as e:
        print(f"⚠️  pgvector extension 설치 실패: {e}")
        print("   (나중에 수동으로 설치할 수 있습니다)")
    
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        print("✅ pg_trgm extension 설치 완료")
    except Exception as e:
        print(f"⚠️  pg_trgm extension 설치 실패: {e}")
    
    cursor.close()
    conn.close()
    
    print("\n🎉 데이터베이스 설정 완료!")


if __name__ == "__main__":
    create_database()
