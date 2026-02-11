"""API 라우터 로드 및 기본 엔드포인트 스모크 테스트.

DB 연결 없이 라우터가 정상 등록되었는지 검증한다.
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
