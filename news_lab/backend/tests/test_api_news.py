from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.models import HeadlineItem
from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/news/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_sources_endpoint():
    response = client.get("/api/news/sources?market=KR")
    assert response.status_code == 200
    data = response.json()
    assert data["market"] == "KR"
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) >= 1


def test_headlines_endpoint_with_monkeypatch(monkeypatch):
    fake_headline = HeadlineItem(
        title="Sample headline",
        url="https://example.com/news",
        source_id="sample",
        source="Sample News",
        published_at=datetime.now(timezone.utc),
        image_url="https://example.com/image.jpg",
    )

    def _fake_fetch_headlines(market, source_id, limit):
        return [fake_headline], []

    monkeypatch.setattr("app.api.routes.news.fetch_headlines", _fake_fetch_headlines)

    response = client.get("/api/news/headlines?market=US")
    assert response.status_code == 200
    data = response.json()
    assert len(data["headlines"]) == 1


def test_analyze_bad_url_returns_400():
    response = client.post(
        "/api/news/analyze",
        json={"url": "file:///tmp/test", "difficulty": "beginner", "market": "KR"},
    )
    assert response.status_code in {400, 422}


def test_analyze_success_with_monkeypatch(monkeypatch):
    fake_payload = {
        "article": {
            "title": "Title",
            "url": "https://example.com/news",
            "source": "example.com",
            "published_at": None,
            "content": "본문",
            "image_url": None,
        },
        "explain_mode": {
            "content_marked": "[[본문]]",
            "highlighted_terms": [{"term": "본문"}],
            "glossary": [],
        },
        "newsletter_mode": {
            "background": "배경",
            "importance": "중요",
            "concepts": ["금리"],
            "related": ["연준"],
            "takeaways": ["체크"],
            "content_marked": "[[배경]]",
            "highlighted_terms": [{"term": "배경"}],
            "glossary": [],
        },
        "highlighted_terms": [{"term": "본문"}],
        "glossary": [],
        "fetch_status": "ok",
        "cached": False,
    }

    async def _fake_analyze(url, difficulty, market):
        return fake_payload

    monkeypatch.setattr("app.api.routes.news.analyze_url", _fake_analyze)

    response = client.post(
        "/api/news/analyze",
        json={"url": "https://example.com/article", "difficulty": "beginner", "market": "KR"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["article"]["title"] == "Title"


def test_visualize_endpoint_with_monkeypatch(monkeypatch):
    async def _fake_visualize(description, data_context):
        return {"success": True, "html": "<div>chart</div>"}

    monkeypatch.setattr("app.api.routes.news.upstream_client.visualize", _fake_visualize)

    response = client.post(
        "/api/news/visualize",
        json={"description": "차트", "data_context": "데이터"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
