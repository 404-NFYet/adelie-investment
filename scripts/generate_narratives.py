"""
새로운 내러티브 생성 파이프라인 (adelie_fe_test/pipeline 기반)
- RSS 피드 및 pykrx로 데이터 수집
- 다단계 AI 파이프라인 (키워드 추출 → 2단계 리서치 → 5단계 스토리 생성)
- 다양성 필터 적용
- daily_narratives, narrative_scenarios 테이블에 저장
- 7단계 내러티브 순서: background, mirroring, simulation, result, difference, devils_advocate, action
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend_api"))

from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
load_dotenv(PROJECT_ROOT / ".env")

from app.pipeline.config import load_config
from app.pipeline.generator import BriefingGenerator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger("generate_narratives")


async def save_to_database(briefing_data: dict, db_url: str):
    """생성된 브리핑 데이터를 DB에 저장."""
    import asyncpg
    
    LOGGER.info("DB에 저장 시작...")
    
    # asyncpg 연결용 URL 형식으로 변환
    clean_url = db_url.replace("+asyncpg", "").replace("postgresql://", "postgres://")
    
    conn = await asyncpg.connect(clean_url)
    
    try:
        today = datetime.now().date()
        
        # 기존 데이터 삭제 (같은 날짜)
        existing = await conn.fetchrow(
            "SELECT id FROM daily_narratives WHERE date = $1", today
        )
        if existing:
            LOGGER.info("오늘(%s) 데이터 이미 존재, 삭제 후 재생성...", today)
            await conn.execute("DELETE FROM daily_narratives WHERE date = $1", today)
        
        # DailyNarrative 생성
        narrative_id = uuid.uuid4()
        main_keywords = briefing_data.get("main_keywords", [])
        glossary = briefing_data.get("glossary", {})
        
        await conn.execute("""
            INSERT INTO daily_narratives (id, date, main_keywords, glossary, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
        """, narrative_id, today, main_keywords, json.dumps(glossary, ensure_ascii=False))
        LOGGER.info("daily_narratives 생성: id=%s", narrative_id)
        
        # NarrativeScenario 생성
        scenarios = briefing_data.get("scenarios", [])
        for i, scenario in enumerate(scenarios):
            scenario_id = uuid.UUID(scenario.get("id", str(uuid.uuid4())))
            
            # narrative를 narrative_sections로 변환
            narrative = scenario.get("narrative", {})
            
            await conn.execute("""
                INSERT INTO narrative_scenarios 
                (id, narrative_id, title, summary, sources, related_companies, mirroring_data, narrative_sections, sort_order, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            """,
                scenario_id,
                narrative_id,
                scenario.get("title", ""),
                scenario.get("summary", ""),
                json.dumps(scenario.get("sources", []), ensure_ascii=False),
                json.dumps(scenario.get("related_companies", []), ensure_ascii=False),
                json.dumps(scenario.get("mirroring_data", {}), ensure_ascii=False),
                json.dumps(narrative, ensure_ascii=False),
                scenario.get("sort_order", i),
            )
            LOGGER.info("narrative_scenarios 생성: title=%s", scenario.get("title", ""))
        
        # 최종 확인
        final_narratives = await conn.fetchval("SELECT COUNT(*) FROM daily_narratives")
        final_scenarios = await conn.fetchval("SELECT COUNT(*) FROM narrative_scenarios")
        
        LOGGER.info("=== 저장 완료 ===")
        LOGGER.info("daily_narratives: %d건", final_narratives)
        LOGGER.info("narrative_scenarios: %d건", final_scenarios)
        
    finally:
        await conn.close()


async def main():
    """메인 파이프라인 실행."""
    LOGGER.info("=== 내러티브 생성 파이프라인 시작 (adelie_fe_test/pipeline 기반) ===")
    
    # 환경 변수 확인
    if not os.getenv("OPENAI_API_KEY"):
        LOGGER.error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        raise SystemExit(1)
    
    if not os.getenv("PERPLEXITY_API_KEY"):
        LOGGER.warning("PERPLEXITY_API_KEY가 설정되지 않았습니다. Perplexity 리서치가 실패할 수 있습니다.")
    
    # 설정 로드
    try:
        config = load_config()
    except RuntimeError as e:
        LOGGER.error("설정 로드 실패: %s", e)
        raise SystemExit(1)
    
    LOGGER.info("설정 로드 완료:")
    LOGGER.info("  - 키워드 모델: %s", config.keyword_model)
    LOGGER.info("  - 리서치 모델: %s", config.research_model)
    LOGGER.info("  - 스토리 모델: %s", config.story_model)
    LOGGER.info("  - 목표 시나리오 수: %d", config.target_scenario_count)
    LOGGER.info("  - RSS 피드: %d개", len(config.rss_feeds))
    LOGGER.info("  - Dry run: %s", config.dry_run)
    
    # Generator 생성 및 실행
    generator = BriefingGenerator(config)
    
    try:
        briefing_data = generator.run()
    except Exception as e:
        LOGGER.exception("브리핑 생성 실패: %s", e)
        raise SystemExit(1)
    
    LOGGER.info("브리핑 생성 완료:")
    LOGGER.info("  - ID: %s", briefing_data.get("id"))
    LOGGER.info("  - 날짜: %s", briefing_data.get("date"))
    LOGGER.info("  - 키워드: %s", briefing_data.get("main_keywords"))
    LOGGER.info("  - 시나리오 수: %d", len(briefing_data.get("scenarios", [])))
    LOGGER.info("  - 용어 사전: %d개", len(briefing_data.get("glossary", {})))
    
    # DB에 저장
    db_url = config.database_url
    LOGGER.info("DB 연결: %s", db_url[:50] + "...")
    
    await save_to_database(briefing_data, db_url)
    
    LOGGER.info("=== 파이프라인 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
