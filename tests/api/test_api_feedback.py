"""피드백 API 엔드포인트 테스트.

기존 backend/test_api_smoke.py 패턴을 따라 동기 TestClient 사용.
DB 연결 없이 스키마 검증(422)과 라우터 등록 확인을 수행한다.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """동기 TestClient — lifespan 이벤트 없이 라우터만 테스트."""
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestFeedbackValidation:
    """피드백 엔드포인트 스키마 검증 테스트 (DB 불필요)."""

    def test_post_feedback_missing_page(self, client):
        """page 필드 누락 → 422."""
        resp = client.post("/api/v1/feedback", json={"rating": 3})
        assert resp.status_code == 422

    def test_post_feedback_invalid_rating(self, client):
        """rating 범위 초과 → 422."""
        resp = client.post("/api/v1/feedback", json={"page": "home", "rating": 10})
        assert resp.status_code == 422

    def test_post_briefing_invalid_rating(self, client):
        """briefing overall_rating 잘못된 값 → 422."""
        resp = client.post(
            "/api/v1/feedback/briefing",
            json={"overall_rating": "excellent"},
        )
        assert resp.status_code == 422

    def test_post_reaction_invalid_type(self, client):
        """content_type 잘못된 값 → 422."""
        resp = client.post(
            "/api/v1/feedback/reaction",
            json={"content_type": "invalid", "content_id": "1", "reaction": "like"},
        )
        assert resp.status_code == 422

    def test_post_survey_invalid_ratings(self, client):
        """설문 rating 범위 초과 → 422."""
        resp = client.post(
            "/api/v1/feedback/survey",
            json={
                "ui_rating": 0,
                "feature_rating": 3,
                "content_rating": 3,
                "speed_rating": 3,
                "overall_rating": 3,
            },
        )
        assert resp.status_code == 422

    def test_post_survey_missing_required(self, client):
        """설문 필수 필드 누락 → 422."""
        resp = client.post(
            "/api/v1/feedback/survey",
            json={"ui_rating": 3, "feature_rating": 3},
        )
        assert resp.status_code == 422


class TestFeedbackRouterRegistered:
    """피드백 관련 라우터가 등록되었는지 확인 (404가 아니면 통과)."""

    def test_feedback_stats_registered(self, client):
        """GET /feedback/stats 라우터 등록 확인."""
        resp = client.get("/api/v1/feedback/stats")
        assert resp.status_code != 404, "feedback/stats 라우터 미등록"

    def test_feedback_survey_registered(self, client):
        """POST /feedback/survey 라우터 등록 확인."""
        resp = client.post(
            "/api/v1/feedback/survey",
            json={
                "ui_rating": 4, "feature_rating": 4, "content_rating": 5,
                "speed_rating": 3, "overall_rating": 4,
            },
        )
        assert resp.status_code != 404, "feedback/survey 라우터 미등록"

    def test_feedback_screenshot_registered(self, client):
        """POST /feedback/screenshot 라우터 등록 확인."""
        resp = client.post("/api/v1/feedback/screenshot")
        assert resp.status_code != 404, "feedback/screenshot 라우터 미등록"
