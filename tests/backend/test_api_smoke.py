"""API 라우터 로드 및 기본 엔드포인트 스모크 테스트.

DB 연결 없이 라우터가 정상 등록되었는지 검증한다.

참고: Playwright E2E에서 이동된 API 헬스체크 케이스 포함
 - /api/v1/health
 - /api/v1/keywords/today
 - /api/v1/narrative/6
 - /api/v1/tutor/sessions
 - /api/v1/tutor/explain/PER
 - /api/v1/keywords/popular
"""

import pytest
from fastapi.testclient import TestClient


# main.py에 선언된 19개 라우터
EXPECTED_ROUTERS = [
    "health",
    "briefing",
    "glossary",
    "cases",
    "tutor",
    "pipeline",
    "highlight",
    "keywords",
    "feedback",
    "trading",
    "narrative",
    "portfolio",
    "tutor_sessions",
    "tutor_explain",
    "visualization",
    "notification",
    "briefings",
    "chat",
    "quiz_reward",
]


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def loaded_routers():
    from app.main import _route_modules
    return _route_modules


class TestRouterLoading:
    """19개 라우터 전부 로드되었는지 확인."""

    def test_all_19_routers_loaded(self, loaded_routers):
        missing = [name for name in EXPECTED_ROUTERS if name not in loaded_routers]
        assert not missing, f"라우터 미로드: {missing}"
        assert len(loaded_routers) >= len(EXPECTED_ROUTERS)

    def test_all_routers_have_router_attribute(self, loaded_routers):
        for name in EXPECTED_ROUTERS:
            mod = loaded_routers.get(name)
            assert mod is not None, f"'{name}' 모듈 없음"
            assert hasattr(mod, "router"), f"'{name}' 모듈에 router 속성 없음"


class TestBasicEndpoints:
    """DB 없이 접근 가능한 기본 엔드포인트."""

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data

    def test_health_endpoint(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_docs_endpoint(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200


class TestApiHealthFromE2E:
    """E2E(Playwright api-health.spec.js)에서 이동된 API 응답 검증.

    실서비스 연동 테스트로, DB가 기동 중인 환경에서만 완전히 통과한다.
    TestClient는 DB 연결이 없으므로 상태코드 200/401/422 범위로만 검증.
    """

    def test_keywords_today_endpoint_registered(self, client):
        """keywords/today 라우터가 등록되어 있어야 한다 (200 또는 DB 오류 제외)."""
        resp = client.get("/api/v1/keywords/today")
        # 라우터 미등록(404)이 아닌 한 통과 (DB 없으면 500 가능)
        assert resp.status_code != 404, "keywords/today 라우터 미등록"

    def test_narrative_endpoint_registered(self, client):
        """narrative/:id 라우터가 등록되어 있어야 한다."""
        resp = client.get("/api/v1/narrative/6")
        assert resp.status_code != 404, "narrative/:id 라우터 미등록"

    def test_tutor_sessions_endpoint_registered(self, client):
        """tutor/sessions 라우터가 등록되어 있어야 한다."""
        resp = client.get("/api/v1/tutor/sessions")
        # 인증 필요 시 401, 정상 시 200
        assert resp.status_code in (200, 401, 422), (
            f"tutor/sessions 예상치 못한 상태코드: {resp.status_code}"
        )

    def test_tutor_explain_endpoint_registered(self, client):
        """tutor/explain/:term 라우터가 등록되어 있어야 한다."""
        resp = client.get("/api/v1/tutor/explain/PER")
        assert resp.status_code != 404, "tutor/explain/:term 라우터 미등록"

    def test_keywords_popular_endpoint_registered(self, client):
        """keywords/popular 라우터가 등록되어 있어야 한다."""
        resp = client.get("/api/v1/keywords/popular")
        assert resp.status_code != 404, "keywords/popular 라우터 미등록"
