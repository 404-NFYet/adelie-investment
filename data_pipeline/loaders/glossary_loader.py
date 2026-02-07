"""
주식 용어 시드 데이터 로더
JSON 파일에서 용어를 읽어 PostgreSQL에 저장
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
import sys

# 상위 디렉토리 추가 (backend-api 모델 사용)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend-api"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# .env 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


def get_database_url() -> str:
    """동기 드라이버용 DATABASE_URL 반환"""
    url = os.getenv("DATABASE_URL", "")
    # asyncpg -> psycopg2로 변환
    return url.replace("postgresql+asyncpg", "postgresql+psycopg2")


def load_glossary_seed() -> list[dict]:
    """시드 데이터 JSON 로드"""
    seed_path = Path(__file__).parent.parent / "seed_data" / "glossary_seed.json"
    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("glossary", [])


def create_glossary_table(engine):
    """glossary 테이블 생성 (없으면)"""
    create_sql = """
    CREATE TABLE IF NOT EXISTS glossary (
        id SERIAL PRIMARY KEY,
        term VARCHAR(100) NOT NULL UNIQUE,
        term_en VARCHAR(100),
        abbreviation VARCHAR(20),
        difficulty VARCHAR(20) NOT NULL DEFAULT 'beginner',
        category VARCHAR(20) NOT NULL DEFAULT 'basic',
        definition_short VARCHAR(200) NOT NULL,
        definition_full TEXT,
        example TEXT,
        formula VARCHAR(200),
        related_terms TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_glossary_difficulty ON glossary(difficulty);
    CREATE INDEX IF NOT EXISTS idx_glossary_category ON glossary(category);
    CREATE INDEX IF NOT EXISTS idx_glossary_term ON glossary(term);
    """
    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()
    print("✅ glossary 테이블 생성/확인 완료")


def insert_glossary_data(engine, glossary_list: list[dict]):
    """용어 데이터 삽입 (upsert)"""
    insert_sql = """
    INSERT INTO glossary (
        term, term_en, abbreviation, difficulty, category,
        definition_short, definition_full, example, formula, related_terms,
        created_at, updated_at
    ) VALUES (
        :term, :term_en, :abbreviation, :difficulty, :category,
        :definition_short, :definition_full, :example, :formula, :related_terms,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    )
    ON CONFLICT (term) DO UPDATE SET
        term_en = EXCLUDED.term_en,
        abbreviation = EXCLUDED.abbreviation,
        difficulty = EXCLUDED.difficulty,
        category = EXCLUDED.category,
        definition_short = EXCLUDED.definition_short,
        definition_full = EXCLUDED.definition_full,
        example = EXCLUDED.example,
        formula = EXCLUDED.formula,
        related_terms = EXCLUDED.related_terms,
        updated_at = CURRENT_TIMESTAMP
    """
    
    with engine.connect() as conn:
        for item in glossary_list:
            conn.execute(text(insert_sql), item)
        conn.commit()
    
    print(f"✅ {len(glossary_list)}개 용어 삽입/업데이트 완료")


def get_glossary_stats(engine) -> dict:
    """용어 통계 조회"""
    stats_sql = """
    SELECT 
        difficulty,
        COUNT(*) as count
    FROM glossary
    GROUP BY difficulty
    ORDER BY 
        CASE difficulty
            WHEN 'beginner' THEN 1
            WHEN 'elementary' THEN 2
            WHEN 'intermediate' THEN 3
        END
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(stats_sql))
        stats = {row[0]: row[1] for row in result}
    
    return stats


def main():
    """메인 실행"""
    print("=" * 50)
    print("📚 주식 용어 시드 데이터 로더")
    print("=" * 50)
    
    # DB 연결
    db_url = get_database_url()
    if not db_url:
        print("❌ DATABASE_URL이 설정되지 않았습니다.")
        return
    
    print(f"🔗 DB 연결: {db_url.split('@')[1] if '@' in db_url else db_url}")
    
    try:
        engine = create_engine(db_url)
        
        # 테이블 생성
        create_glossary_table(engine)
        
        # 시드 데이터 로드
        glossary_list = load_glossary_seed()
        print(f"📄 시드 데이터: {len(glossary_list)}개 용어")
        
        # 데이터 삽입
        insert_glossary_data(engine, glossary_list)
        
        # 통계 출력
        stats = get_glossary_stats(engine)
        print("\n📊 난이도별 용어 수:")
        difficulty_labels = {
            "beginner": "입문",
            "elementary": "초급", 
            "intermediate": "중급"
        }
        for diff, count in stats.items():
            label = difficulty_labels.get(diff, diff)
            print(f"   - {label}: {count}개")
        
        total = sum(stats.values())
        print(f"   - 총계: {total}개")
        
        print("\n✅ 완료!")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        raise


if __name__ == "__main__":
    main()
