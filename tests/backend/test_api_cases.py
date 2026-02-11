"""
Cases API Tests
"""

import pytest
from fastapi.testclient import TestClient


class TestCasesAPI:
    """Cases API tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)
    
    def test_search_cases_returns_200(self):
        """GET /search/cases should return 200."""
        response = self.client.get("/api/v1/search/cases?query=반도체")
        assert response.status_code == 200
    
    def test_search_cases_requires_query(self):
        """GET /search/cases requires query parameter."""
        response = self.client.get("/api/v1/search/cases")
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_search_cases_response_structure(self):
        """Search cases response should have expected structure."""
        response = self.client.get("/api/v1/search/cases?query=테스트")
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "cases" in data
        assert "search_source" in data
        assert isinstance(data["cases"], list)
    
    def test_search_cases_with_recency_filter(self):
        """GET /search/cases with recency filter."""
        response = self.client.get("/api/v1/search/cases?query=테스트&recency=month")
        assert response.status_code == 200
    
    def test_search_cases_with_limit(self):
        """GET /search/cases with limit parameter."""
        response = self.client.get("/api/v1/search/cases?query=테스트&limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["cases"]) <= 3
    
    def test_get_story_not_found(self):
        """GET /story/{case_id} with invalid id returns 404."""
        response = self.client.get("/api/v1/story/99999")
        assert response.status_code == 404
    
    def test_get_comparison_not_found(self):
        """GET /comparison/{case_id} with invalid id returns 404."""
        response = self.client.get("/api/v1/comparison/99999")
        assert response.status_code == 404
    
    def test_get_companies_not_found(self):
        """GET /companies/{case_id} with invalid id returns 404."""
        response = self.client.get("/api/v1/companies/99999")
        assert response.status_code == 404
