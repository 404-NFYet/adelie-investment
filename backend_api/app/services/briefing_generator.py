"""Briefing Generator - 내러티브 브리핑 생성."""
import uuid
import asyncio
from datetime import date
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_pipeline_service import get_ai_pipeline_service
from app.services.rss_service import get_rss_service
from app.models.narrative import DailyNarrative, NarrativeScenario

class BriefingGenerator:
    def __init__(self):
        self.ai_service = get_ai_pipeline_service()
        self.rss_service = get_rss_service()

    async def generate_daily_briefing(self, db: AsyncSession, target_date: date = None):
        target_date = target_date or date.today()
        
        # 1. RSS 뉴스 수집
        news = await self.rss_service.fetch_all_feeds()
        news_text = "\n".join([f"- {n[\"title\"]}" for n in news[:20]])
        
        # 2. 키워드 추출
        keywords = await self.ai_service.call_openai(
            [{"role": "user", "content": f"다음 뉴스에서 핵심 키워드 5개를 JSON으로:\n{news_text}"}],
            temp=0.3
        )
        
        # 3. DailyNarrative 생성
        narrative = DailyNarrative(
            id=uuid.uuid4(),
            date=target_date,
            main_keywords=[],
            glossary={},
        )
        db.add(narrative)
        
        # 4. 시나리오 생성 (간소화 버전)
        scenario = NarrativeScenario(
            id=uuid.uuid4(),
            narrative_id=narrative.id,
            title="오늘의 시장 동향",
            summary="시장 분석 요약",
            sort_order=0,
        )
        db.add(scenario)
        
        await db.commit()
        return narrative

_instance = None
def get_briefing_generator():
    global _instance
    if not _instance:
        _instance = BriefingGenerator()
    return _instance

