import anyio
import pytest

from app.services.analyzer import (
    AnalyzeError,
    _build_marked_text,
    _extract_numeric_evidence,
    _normalize_glossary,
    _render_newsletter_text,
    analyze_url,
)
from app.services.article_service import ArticleData


def test_normalize_glossary_limits_and_filters():
    payload = {
        "glossary": {
            "words": [
                {"term": "금리", "definition": "기준금리", "importance": 5},
                {"term": "시장", "definition": "일반 단어", "importance": 5},
                {"term": "Inflation", "definition": "물가", "importance": 4},
                {"term": "GDP", "definition": "국내총생산", "importance": 4},
                {"term": "CPI", "definition": "소비자물가", "importance": 4},
                {"term": "PER", "definition": "주가수익비율", "importance": 4},
                {"term": "EPS", "definition": "주당순이익", "importance": 4},
                {"term": "ROE", "definition": "자기자본이익률", "importance": 4},
            ],
            "phrases": [
                {"term": "신용카드 결제 비중", "definition": "결제 변화", "importance": 5},
                {"term": "현금 사용 비중 감소", "definition": "소비 행태 변화", "importance": 4},
                {"term": "포인트 적립 혜택", "definition": "소비자 동기", "importance": 4},
                {"term": "", "definition": "bad", "importance": 4},
                {"term": "12345", "definition": "bad", "importance": 4},
                {"term": "물가 상승 압박", "definition": "거시 여건", "importance": 4},
                {"term": "인터넷 쇼핑 확산", "definition": "채널 전환", "importance": 3},
                {"term": "지불 수단 변화", "definition": "핵심 맥락", "importance": 5},
            ],
        }
    }

    glossary = _normalize_glossary(payload, "fallback text")
    words = [g for g in glossary if g["kind"] == "word"]
    phrases = [g for g in glossary if g["kind"] == "phrase"]

    assert len(words) <= 6
    assert len(phrases) <= 6
    assert all(item["term"] != "시장" for item in words)


def test_build_marked_text_phrase_priority_single_occurrence():
    text = "신용카드 결제 비중이 올랐고 신용카드 결제 비중이 다시 언급됐다. 금리는 하락했다."
    glossary = [
        {"term": "신용카드 결제 비중", "definition": "", "kind": "phrase", "importance": 5},
        {"term": "금리", "definition": "", "kind": "word", "importance": 4},
    ]

    marked = _build_marked_text(text, glossary)

    assert marked.count("data-term='신용카드 결제 비중'") == 1
    assert marked.count("data-term='금리'") == 1


def test_render_newsletter_text_has_no_markdown_heading():
    rendered = _render_newsletter_text(
        {
            "background": "배경",
            "importance": "중요",
            "concepts": ["금리", "환율"],
            "related": ["연준"],
            "takeaways": ["첫째", "둘째"],
        }
    )
    assert "###" not in rendered
    assert rendered.startswith("배경:")


def test_extract_numeric_evidence_detects_finance_numbers():
    text = "코스피는 2,845포인트를 기록했고 환율은 1,370원으로 0.5% 하락했다."
    evidence = _extract_numeric_evidence(text)
    assert any("%" in item for item in evidence)
    assert any("원" in item for item in evidence)


def test_analyze_url_rejects_non_finance_article(monkeypatch):
    article = ArticleData(
        title="민주당 복당 신청",
        url="https://example.com/politics",
        source="example.com",
        published_at=None,
        content="국회와 여야가 복당 문제를 두고 공방을 이어갔다.",
        image_url=None,
        article_domain="example.com",
        content_quality_score=90,
        quality_flags=[],
    )

    async def _fake_run_sync(func, url):
        return article

    async def _cache_miss(_key):
        return None

    async def _cache_set(_key, _value):
        return None

    monkeypatch.setattr("app.services.analyzer.anyio.to_thread.run_sync", _fake_run_sync)
    monkeypatch.setattr("app.services.analyzer.cache_backend.get_json", _cache_miss)
    monkeypatch.setattr("app.services.analyzer.cache_backend.set_json", _cache_set)
    async def _run():
        with pytest.raises(AnalyzeError) as exc:
            await analyze_url(article.url, "beginner", "KR")
        assert exc.value.code == "NON_FINANCE_ARTICLE"

    anyio.run(_run)


def test_analyze_url_sets_chart_gate(monkeypatch):
    article = ArticleData(
        title="코스피 상승",
        url="https://example.com/finance",
        source="example.com",
        published_at=None,
        content="코스피는 2,845포인트를 회복했고 환율은 1,370원으로 0.5% 하락했다.",
        image_url=None,
        article_domain="example.com",
        content_quality_score=88,
        quality_flags=[],
    )

    async def _fake_run_sync(func, url):
        return article

    async def _cache_miss(_key):
        return None

    async def _cache_set(_key, _value):
        return None

    async def _fake_llm(*_args, **_kwargs):
        return None

    async def _fake_highlight(content, difficulty, custom_terms):
        return content, []

    monkeypatch.setattr("app.services.analyzer.anyio.to_thread.run_sync", _fake_run_sync)
    monkeypatch.setattr("app.services.analyzer.cache_backend.get_json", _cache_miss)
    monkeypatch.setattr("app.services.analyzer.cache_backend.set_json", _cache_set)
    monkeypatch.setattr("app.services.analyzer._llm_payload", _fake_llm)
    monkeypatch.setattr("app.services.analyzer.upstream_client.highlight_content", _fake_highlight)

    async def _run():
        result = await analyze_url(article.url, "beginner", "KR")
        assert result["chart_ready"] is True
        assert result["chart_unavailable_reason"] is None

    anyio.run(_run)
