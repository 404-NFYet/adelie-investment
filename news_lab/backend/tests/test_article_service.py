import pytest

from app.services.article_service import ArticleExtractionError, fetch_article


class _DummyResponse:
    def __init__(self, text: str, status_code: int = 200, encoding: str = "utf-8", apparent_encoding: str = "utf-8"):
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code
        self.encoding = encoding
        self.apparent_encoding = apparent_encoding

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


def test_fetch_article_extracts_title_content_and_image(monkeypatch):
    html = """
    <html>
      <head>
        <meta property='og:title' content='Test Title'>
        <meta property='og:image' content='https://example.com/main.jpg'>
      </head>
      <body>
        <article>
          <p>{}</p>
        </article>
      </body>
    </html>
    """.format("word " * 300)

    def _fake_get(*args, **kwargs):
        return _DummyResponse(html)

    monkeypatch.setattr("app.services.article_service.requests.get", _fake_get)

    article = fetch_article("https://example.com/article")
    assert article.title == "Test Title"
    assert "word" in article.content
    assert article.source == "example.com"
    assert article.image_url == "https://example.com/main.jpg"


def test_fetch_article_raises_on_short_content(monkeypatch):
    html = "<html><body><article><p>too short</p></article></body></html>"

    def _fake_get(*args, **kwargs):
        return _DummyResponse(html)

    monkeypatch.setattr("app.services.article_service.requests.get", _fake_get)

    with pytest.raises(ArticleExtractionError):
        fetch_article("https://example.com/article")


def test_fetch_article_handles_mojibake_source_encoding(monkeypatch):
    html = """
    <html>
      <head>
        <meta property='og:title' content='이 대통령 "R&D 생태계 복원"'>
      </head>
      <body>
        <div id='NewsViewCont'>{}</div>
      </body>
    </html>
    """.format("한글 본문 " * 80)

    def _fake_get(*args, **kwargs):
        return _DummyResponse(html, encoding="ISO-8859-1", apparent_encoding="utf-8")

    monkeypatch.setattr("app.services.article_service.requests.get", _fake_get)

    article = fetch_article("https://mbnmoney.mbn.co.kr/news/view?news_no=test")
    assert "이 대통령" in article.title
    assert "한글 본문" in article.content
