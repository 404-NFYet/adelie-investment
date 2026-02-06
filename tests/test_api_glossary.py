"""Glossary API Tests."""
import pytest
from fastapi.testclient import TestClient

class TestGlossaryAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        from app.main import app
        self.client = TestClient(app)
    
    def test_get_glossary_returns_200(self):
        response = self.client.get("/api/v1/glossary")
        assert response.status_code == 200
    
    def test_get_glossary_has_items(self):
        response = self.client.get("/api/v1/glossary")
        data = response.json()
        assert "items" in data
    
    def test_get_glossary_with_filter(self):
        response = self.client.get("/api/v1/glossary?difficulty=beginner")
        assert response.status_code == 200
