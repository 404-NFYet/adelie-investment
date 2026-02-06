"""
AI Tutor API Tests
"""

import pytest
from fastapi.testclient import TestClient


class TestTutorAPI:
    """AI Tutor API tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)
    
    def test_tutor_chat_returns_stream(self):
        """POST /tutor/chat should return SSE stream."""
        response = self.client.post(
            "/api/v1/tutor/chat",
            json={"message": "PER이 뭐야?"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
    
    def test_tutor_chat_requires_message(self):
        """POST /tutor/chat requires message field."""
        response = self.client.post(
            "/api/v1/tutor/chat",
            json={},
        )
        assert response.status_code == 422
    
    def test_tutor_chat_with_difficulty(self):
        """POST /tutor/chat with difficulty parameter."""
        response = self.client.post(
            "/api/v1/tutor/chat",
            json={
                "message": "주식이 뭐야?",
                "difficulty": "beginner",
            },
        )
        assert response.status_code == 200
    
    def test_tutor_chat_with_session_id(self):
        """POST /tutor/chat with session_id parameter."""
        response = self.client.post(
            "/api/v1/tutor/chat",
            json={
                "message": "테스트 질문",
                "session_id": "test-session-123",
            },
        )
        assert response.status_code == 200
    
    def test_tutor_chat_with_context(self):
        """POST /tutor/chat with context parameters."""
        response = self.client.post(
            "/api/v1/tutor/chat",
            json={
                "message": "이 사례에 대해 더 설명해줘",
                "context_type": "case",
                "context_id": 1,
            },
        )
        assert response.status_code == 200
