"""Schema validation tests."""
import pytest
from pydantic import ValidationError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "fastapi"))

from app.schemas.briefing import BriefingStock, BriefingResponse
from app.schemas.case import CaseSearchRequest, HistoricalCase
from app.schemas.glossary import GlossaryItem
from app.schemas.tutor import TutorChatRequest
from app.schemas.pipeline import PipelineTriggerRequest


class TestBriefingSchemas:
    def test_briefing_stock_valid(self):
        stock = BriefingStock(
            stock_code="005930",
            stock_name="삼성전자",
            change_rate=2.5,
            volume=1000000,
            selection_reason="top_gainer"
        )
        assert stock.stock_code == "005930"
    
    def test_briefing_stock_invalid_reason(self):
        with pytest.raises(ValidationError):
            BriefingStock(
                stock_code="005930",
                stock_name="삼성전자",
                change_rate=2.5,
                volume=1000000,
                selection_reason="invalid_reason"
            )


class TestCaseSchemas:
    def test_case_search_request_default(self):
        req = CaseSearchRequest(query="반도체")
        assert req.recency == "year"
        assert req.limit == 5
    
    def test_historical_case_valid(self):
        case = HistoricalCase(
            id=1,
            title="테스트 사례",
            event_year=2020,
            summary="테스트 요약",
            keywords=["테스트"],
            similarity_score=0.9
        )
        assert case.id == 1


class TestGlossarySchemas:
    def test_glossary_item_valid(self):
        item = GlossaryItem(
            id=1,
            term="PER",
            difficulty="beginner",
            category="indicator",
            definition_short="주가수익비율"
        )
        assert item.term == "PER"


class TestTutorSchemas:
    def test_tutor_request_default(self):
        req = TutorChatRequest(message="테스트 질문")
        assert req.difficulty == "beginner"
        assert req.session_id is None


class TestPipelineSchemas:
    def test_pipeline_request_valid(self):
        req = PipelineTriggerRequest(tasks=["stock"])
        assert len(req.tasks) == 1
