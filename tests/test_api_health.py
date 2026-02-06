"""FastAPI Health Endpoint Tests."""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        from app.main import app
        self.client = TestClient(app)
    
    def test_health_returns_200(self):
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200
    
    def test_health_returns_json(self):
        response = self.client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
