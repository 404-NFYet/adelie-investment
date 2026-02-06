"""
AI QA 환각(Hallucination) 테스트
AI 모델이 사실과 다른 정보를 생성하는지 검증합니다.

테스트 카테고리:
1. 사실 검증 - 실제 주식/기업 정보가 정확한지
2. 시간 일관성 - 과거 사례의 날짜가 정확한지
3. 수치 정확성 - 주가, 시가총액 등 수치가 합리적인지
4. 관계 정확성 - 기업 간 관계, 공급망이 정확한지
"""
import asyncio
import pytest
from typing import Optional
import httpx

API_BASE_URL = "http://localhost:8082/api/v1"


class TestFactualAccuracy:
    """사실 검증 테스트"""
    
    @pytest.mark.asyncio
    async def test_company_exists(self):
        """실제 존재하는 기업 정보만 반환하는지 테스트"""
        test_cases = [
            {"name": "삼성전자", "code": "005930", "should_exist": True},
            {"name": "SK하이닉스", "code": "000660", "should_exist": True},
            {"name": "가짜회사", "code": "999999", "should_exist": False},
        ]
        
        async with httpx.AsyncClient() as client:
            for case in test_cases:
                response = await client.get(
                    f"{API_BASE_URL}/market/company/{case['code']}"
                )
                if case["should_exist"]:
                    assert response.status_code == 200, f"{case['name']} should exist"
                else:
                    assert response.status_code == 404, f"{case['name']} should not exist"
    
    @pytest.mark.asyncio
    async def test_glossary_accuracy(self):
        """용어집 정의의 정확성 테스트"""
        test_terms = [
            {"term": "PER", "must_contain": ["주가", "수익", "비율"]},
            {"term": "시가총액", "must_contain": ["주가", "주식수"]},
            {"term": "배당", "must_contain": ["이익", "주주"]},
        ]
        
        async with httpx.AsyncClient() as client:
            for term_data in test_terms:
                response = await client.get(
                    f"{API_BASE_URL}/glossary/search",
                    params={"term": term_data["term"]}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        definition = data[0].get("definition_short", "") + data[0].get("definition_full", "")
                        for keyword in term_data["must_contain"]:
                            assert keyword in definition, f"'{term_data['term']}' 정의에 '{keyword}'가 포함되어야 함"


class TestTemporalConsistency:
    """시간 일관성 테스트"""
    
    @pytest.mark.asyncio
    async def test_historical_case_dates(self):
        """역사적 사례의 날짜가 논리적인지 테스트"""
        known_events = [
            {"event": "닷컴버블", "year_range": (1999, 2001)},
            {"event": "2008금융위기", "year_range": (2007, 2009)},
            {"event": "코로나", "year_range": (2020, 2021)},
        ]
        
        # This would test the historical case API responses
        # to ensure dates are within expected ranges
        pass  # Implement when API is ready
    
    @pytest.mark.asyncio
    async def test_no_future_data(self):
        """미래 데이터를 과거 데이터로 제시하지 않는지 테스트"""
        from datetime import datetime
        current_year = datetime.now().year
        
        # Test that any historical case doesn't reference future dates
        pass  # Implement when API is ready


class TestNumericalAccuracy:
    """수치 정확성 테스트"""
    
    @pytest.mark.asyncio
    async def test_stock_price_range(self):
        """주가가 합리적인 범위 내인지 테스트"""
        # Korean stock prices should generally be > 0 and < 10,000,000 won
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/market/top-movers")
            if response.status_code == 200:
                data = response.json()
                for stock in data.get("gainers", []) + data.get("losers", []):
                    price = stock.get("price", 0)
                    assert 0 < price < 10_000_000, f"Stock price {price} is out of range"
    
    @pytest.mark.asyncio
    async def test_percentage_range(self):
        """변동률이 합리적인 범위 내인지 테스트 (상한가/하한가 고려)"""
        # Korean stocks have daily limits of ±30%
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/market/top-movers")
            if response.status_code == 200:
                data = response.json()
                for stock in data.get("gainers", []) + data.get("losers", []):
                    change = stock.get("change_rate", 0)
                    assert -30 <= change <= 30, f"Change rate {change}% exceeds daily limit"


class TestRelationshipAccuracy:
    """관계 정확성 테스트"""
    
    @pytest.mark.asyncio
    async def test_supply_chain_consistency(self):
        """공급망 관계가 일관성 있는지 테스트"""
        # If A supplies to B, B should list A as supplier
        pass  # Implement when Neo4j queries are ready
    
    @pytest.mark.asyncio
    async def test_sector_classification(self):
        """기업 섹터 분류가 정확한지 테스트"""
        known_classifications = [
            {"name": "삼성전자", "sector": "전기전자"},
            {"name": "현대차", "sector": "운수장비"},
            {"name": "삼성바이오로직스", "sector": "의약품"},
        ]
        
        # Verify sector classifications match official KOSPI/KOSDAQ categories
        pass  # Implement when API is ready


class TestHighlightAccuracy:
    """용어 하이라이팅 정확성 테스트"""
    
    @pytest.mark.asyncio
    async def test_highlight_real_terms(self):
        """실제 금융 용어만 하이라이팅하는지 테스트"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/highlight",
                json={
                    "content": "삼성전자의 PER은 15배이고, 가짜용어는 없습니다.",
                    "difficulty": "beginner"
                }
            )
            if response.status_code == 200:
                data = response.json()
                highlighted = [t["term"] for t in data.get("highlighted_terms", [])]
                assert "PER" in highlighted, "PER should be highlighted"
                assert "가짜용어" not in highlighted, "Fake terms should not be highlighted"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
