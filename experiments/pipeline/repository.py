"""PostgreSQL 리포지토리 - 실험용 직접 DB 접근.

SQLAlchemy async + asyncpg를 사용한 독립 DB 레이어.
프로덕션 ORM 모델 없이 raw SQL로 동작하며, 로컬 실험에 사용.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pipeline.config import PipelineConfig

LOGGER = logging.getLogger(__name__)


class PipelineRepository:
    """파이프라인 결과 저장/조회용 리포지토리 (실험용)."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        cfg = config or PipelineConfig()
        self.database_url = cfg.database_url
        self._engine = None
        self._session_factory = None

    async def _get_session(self) -> AsyncSession:
        """세션 팩토리 초기화 및 세션 반환."""
        if self._engine is None:
            if not self.database_url:
                raise RuntimeError("DATABASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요.")

            # asyncpg 드라이버로 변환
            url = self.database_url
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

            self._engine = create_async_engine(url, echo=False, pool_size=5)
            self._session_factory = sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False,
            )

        return self._session_factory()

    async def save_pipeline_result(
        self,
        target_date: date,
        keywords: list[str],
        scenarios: list[dict[str, Any]],
        glossary: dict[str, str],
    ) -> str:
        """파이프라인 결과를 DB에 저장.

        Returns:
            생성된 narrative ID (UUID)
        """
        narrative_id = str(uuid.uuid4())
        session = await self._get_session()

        try:
            async with session.begin():
                # daily_narratives 테이블에 삽입
                await session.execute(
                    text("""
                        INSERT INTO daily_narratives (id, date, main_keywords, glossary, created_at)
                        VALUES (:id, :date, :keywords, :glossary, :created_at)
                        ON CONFLICT (date) DO UPDATE SET
                            main_keywords = EXCLUDED.main_keywords,
                            glossary = EXCLUDED.glossary,
                            created_at = EXCLUDED.created_at
                    """),
                    {
                        "id": narrative_id,
                        "date": target_date,
                        "keywords": json.dumps(keywords, ensure_ascii=False),
                        "glossary": json.dumps(glossary, ensure_ascii=False),
                        "created_at": datetime.now(timezone.utc),
                    },
                )

                # narrative_scenarios 테이블에 삽입
                for idx, scenario in enumerate(scenarios):
                    scenario_id = str(uuid.uuid4())
                    await session.execute(
                        text("""
                            INSERT INTO narrative_scenarios
                                (id, narrative_id, title, summary, sources,
                                 related_companies, mirroring_data, narrative_sections, sort_order)
                            VALUES
                                (:id, :narrative_id, :title, :summary, :sources,
                                 :companies, :mirroring, :sections, :sort_order)
                        """),
                        {
                            "id": scenario_id,
                            "narrative_id": narrative_id,
                            "title": scenario.get("title", ""),
                            "summary": scenario.get("summary", ""),
                            "sources": json.dumps(scenario.get("sources", []), ensure_ascii=False),
                            "companies": json.dumps(scenario.get("related_companies", []), ensure_ascii=False),
                            "mirroring": json.dumps(scenario.get("mirroring_data", {}), ensure_ascii=False),
                            "sections": json.dumps(scenario.get("narrative", {}), ensure_ascii=False),
                            "sort_order": idx,
                        },
                    )

            LOGGER.info("Saved pipeline result: date=%s id=%s scenarios=%d", target_date, narrative_id, len(scenarios))
            return narrative_id

        except Exception as exc:
            LOGGER.error("Failed to save pipeline result: %s", exc)
            raise
        finally:
            await session.close()

    async def get_latest_briefing(self, target_date: date | None = None) -> dict[str, Any] | None:
        """최신 브리핑 조회."""
        session = await self._get_session()
        try:
            if target_date:
                result = await session.execute(
                    text("SELECT * FROM daily_narratives WHERE date = :date"),
                    {"date": target_date},
                )
            else:
                result = await session.execute(
                    text("SELECT * FROM daily_narratives ORDER BY date DESC LIMIT 1"),
                )
            row = result.mappings().first()
            return dict(row) if row else None
        finally:
            await session.close()

    async def check_existing(self, target_date: date) -> bool:
        """특정 날짜 브리핑 존재 여부 확인."""
        session = await self._get_session()
        try:
            result = await session.execute(
                text("SELECT COUNT(*) as cnt FROM daily_narratives WHERE date = :date"),
                {"date": target_date},
            )
            row = result.mappings().first()
            return (row["cnt"] if row else 0) > 0
        finally:
            await session.close()

    async def close(self) -> None:
        """엔진 정리."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
