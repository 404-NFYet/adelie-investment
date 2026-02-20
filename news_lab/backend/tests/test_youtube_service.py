from app.services.article_service import ArticleExtractionError
from app.services.youtube_service import (
    _fetch_transcript_text,
    extract_video_id,
)


def test_extract_video_id_supports_multiple_url_patterns():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/live/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_fetch_transcript_uses_ytdlp_fallback(monkeypatch):
    def _primary(_video_id, _max_chars):
        raise ArticleExtractionError("primary failed", code="YOUTUBE_TRANSCRIPT_FAILED")

    def _fallback(_url, _max_chars):
        return "자막 데이터 " * 120, "automatic:ko:vtt"

    monkeypatch.setattr("app.services.youtube_service._fetch_transcript_primary", _primary)
    monkeypatch.setattr("app.services.youtube_service._fetch_transcript_via_ytdlp", _fallback)

    text, source = _fetch_transcript_text("dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ", 4000)
    assert len(text) >= 200
    assert source.startswith("automatic")


def test_fetch_transcript_raises_when_both_fail(monkeypatch):
    def _primary(_video_id, _max_chars):
        raise ArticleExtractionError("no element found", code="YOUTUBE_TRANSCRIPT_FAILED")

    def _fallback(_url, _max_chars):
        raise ArticleExtractionError("yt-dlp track missing", code="YOUTUBE_TRANSCRIPT_FAILED")

    monkeypatch.setattr("app.services.youtube_service._fetch_transcript_primary", _primary)
    monkeypatch.setattr("app.services.youtube_service._fetch_transcript_via_ytdlp", _fallback)

    try:
        _fetch_transcript_text("dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ", 4000)
        assert False, "expected ArticleExtractionError"
    except ArticleExtractionError as exc:
        assert exc.code == "YOUTUBE_TRANSCRIPT_FAILED"
        assert "primary" in str(exc)
        assert "fallback" in str(exc)
