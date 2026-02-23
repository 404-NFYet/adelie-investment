"""질문 의도 분류 유닛 테스트 (7개)."""
import pytest
from app.services.query_presets import classify_intent


class TestClassifyIntent:
    """키워드 기반 의도 분류 테스트."""

    def test_stock_analysis_intent(self):
        """주가/분석 관련 키워드 → stock_analysis."""
        assert classify_intent("삼성전자 주가 전망이 어때?") == "stock_analysis"
        assert classify_intent("PER이 낮은 종목 분석해줘") == "stock_analysis"

    def test_market_overview_intent(self):
        """시장/브리핑 관련 키워드 → market_overview."""
        assert classify_intent("오늘 시장 이슈가 뭐야?") == "market_overview"
        assert classify_intent("코스피 시황 알려줘") == "market_overview"

    def test_glossary_intent(self):
        """용어/개념 관련 키워드 → glossary."""
        assert classify_intent("PBR이 무슨 뜻이야?") == "glossary"
        assert classify_intent("배당수익률 개념 설명해줘") == "glossary"

    def test_historical_case_intent(self):
        """과거 사례 관련 키워드 → historical_case."""
        assert classify_intent("과거에 비슷한 사례가 있었어?") == "historical_case"
        assert classify_intent("역사적으로 반복되는 패턴") == "historical_case"

    def test_comparison_intent(self):
        """비교 관련 키워드 → comparison."""
        assert classify_intent("삼성전자 vs SK하이닉스 비교해줘") == "comparison"
        assert classify_intent("두 종목 차이가 뭐야?") == "comparison"

    def test_general_intent(self):
        """매칭 키워드 없으면 general."""
        assert classify_intent("안녕하세요") == "general"
        assert classify_intent("도움이 필요해요") == "general"

    def test_highest_score_wins(self):
        """여러 의도가 매칭되면 점수가 높은 것이 선택됨."""
        # "주가 전망 분석 거래량" → stock_analysis (4키워드) vs market_overview (0)
        result = classify_intent("주가 전망 분석 거래량 수급")
        assert result == "stock_analysis"
