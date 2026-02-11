"""
Pipeline API Tests
"""

import pytest
from fastapi.testclient import TestClient


class TestPipelineAPI:
    """Pipeline API tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)
    
    def test_trigger_pipeline_returns_200(self):
        """POST /pipeline/trigger should return 200."""
        response = self.client.post(
            "/api/v1/pipeline/trigger",
            json={"tasks": ["stock"]},
        )
        assert response.status_code == 200
    
    def test_trigger_pipeline_requires_tasks(self):
        """POST /pipeline/trigger requires tasks field."""
        response = self.client.post(
            "/api/v1/pipeline/trigger",
            json={},
        )
        assert response.status_code == 422
    
    def test_trigger_pipeline_response_structure(self):
        """Pipeline trigger response should have expected structure."""
        response = self.client.post(
            "/api/v1/pipeline/trigger",
            json={"tasks": ["stock"]},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert "results" in data
        assert "total_duration" in data
        assert isinstance(data["results"], list)
    
    def test_trigger_multiple_tasks(self):
        """POST /pipeline/trigger with multiple tasks."""
        response = self.client.post(
            "/api/v1/pipeline/trigger",
            json={"tasks": ["stock", "report"]},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 2
    
    def test_trigger_pipeline_with_date(self):
        """POST /pipeline/trigger with date parameter."""
        response = self.client.post(
            "/api/v1/pipeline/trigger",
            json={
                "tasks": ["stock"],
                "date": "20260131",
            },
        )
        assert response.status_code == 200
    
    def test_get_pipeline_status(self):
        """GET /pipeline/status/{job_id} should return status."""
        response = self.client.get("/api/v1/pipeline/status/test-job-123")
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert "status" in data
