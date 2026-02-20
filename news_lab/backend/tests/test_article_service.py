import pytest

from app.services.article_service import ArticleExtractionError, evaluate_content_quality, fetch_article


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
    assert article.content_quality_score >= 45
    assert article.article_domain == "example.com"


def test_fetch_article_strips_ui_noise(monkeypatch):
    body_text = (
        "국내 증시는 미국 금리 인하 기대에 따라 오전 장에서 상승했고 "
        "외국인 순매수 규모가 확대되며 코스피 지수는 1.7% 올랐다. "
        "기업 실적 전망 상향이 이어지면서 반도체 업종 중심으로 매수세가 유입됐다. "
        "기관은 단기 차익 실현 매물을 내놓았지만 시장 전반의 위험 선호는 유지됐다. "
    ) * 6

    html = """
    <html>
      <head><meta property='og:title' content='노이즈 제거 테스트'></head>
      <body>
        <header>구독하기 공유 댓글 0</header>
        <nav>글자크기 조절 기사 스크랩</nav>
        <article>
          <p>{body_text}</p>
          <p>구독하기 기사 스크랩 프린트</p>
        </article>
        <footer>저작권자 © 한국경제 무단전재 및 재배포 금지</footer>
      </body>
    </html>
    """.format(body_text=body_text)

    def _fake_get(*args, **kwargs):
        return _DummyResponse(html)

    monkeypatch.setattr("app.services.article_service.requests.get", _fake_get)

    article = fetch_article("https://example.com/article")
    assert "구독하기" not in article.content
    assert "기사 스크랩" not in article.content
    assert "저작권" not in article.content
    assert "코스피" in article.content


def test_fetch_article_raises_low_quality_code(monkeypatch):
    html = "<html><body><article><p>dummy</p></article></body></html>"
    low_quality = ("구독하기 기사 스크랩 공유 댓글 0 " * 80) + "기자 foo@example.com"

    def _fake_get(*args, **kwargs):
        return _DummyResponse(html)

    monkeypatch.setattr("app.services.article_service.requests.get", _fake_get)
    monkeypatch.setattr("app.services.article_service._collect_candidates", lambda _url, _soup: [low_quality])

    with pytest.raises(ArticleExtractionError) as exc:
        fetch_article("https://example.com/article")
    assert exc.value.code == "LOW_CONTENT_QUALITY"


def test_fetch_article_handles_mojibake_source_encoding(monkeypatch):
    korean_body = (
        "정부는 연구개발 투자 규모를 확대하고 기초연구 지원 비중을 17%까지 높이겠다고 밝혔다. "
        "산업계는 이번 정책이 반도체와 바이오 분야의 중장기 경쟁력 강화에 도움이 된다고 평가했다. "
        "전문가들은 예산 집행의 속도와 민간 투자 유인 설계가 성과를 좌우할 것이라고 전망했다. "
    ) * 4

    html = """
    <html>
      <head>
        <meta property='og:title' content='이 대통령 "R&D 생태계 복원"'>
      </head>
      <body>
        <article><p>{}</p></article>
      </body>
    </html>
    """.format(korean_body)

    def _fake_get(*args, **kwargs):
        return _DummyResponse(html, encoding="ISO-8859-1", apparent_encoding="utf-8")

    monkeypatch.setattr("app.services.article_service.requests.get", _fake_get)

    article = fetch_article("https://mbnmoney.mbn.co.kr/news/view?news_no=test")
    assert "이 대통령" in article.title
    assert "연구개발 투자 규모" in article.content


def test_evaluate_content_quality_flags_boilerplate():
    score, flags = evaluate_content_quality("구독하기 기사 스크랩 공유 댓글 0 " * 100)
    assert score < 45
    assert "boilerplate_heavy" in flags
