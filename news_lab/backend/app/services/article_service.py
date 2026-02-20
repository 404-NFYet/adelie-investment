from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_SELECTORS_BY_DOMAIN: dict[str, list[str]] = {
    "www.hankyung.com": ["div#articletxt", "div.article-body", "div#contents"],
    "hankyung.com": ["div#articletxt", "div.article-body", "div#contents"],
    "www.mk.co.kr": ["div#article_body", "div.article_body", "div#articleBody", "div#content"],
    "mk.co.kr": ["div#article_body", "div.article_body", "div#articleBody", "div#content"],
    "www.asiae.co.kr": ["div#txt_area", "div.news_area", "div#articleBody"],
    "asiae.co.kr": ["div#txt_area", "div.news_area", "div#articleBody"],
    "mbnmoney.mbn.co.kr": [
        "div#NewsViewCont",
        "div#newsViewCont",
        "div.news_contents",
        "div#news_contents",
        "div#newsContent",
        "div#article_body",
        "div.view_cont",
    ],
    "www.marketwatch.com": ["div.article__body", "article.article__body", "div#article-body"],
    "marketwatch.com": ["div.article__body", "article.article__body", "div#article-body"],
    "finance.yahoo.com": ["div.caas-body", "article"],
    "biz.chosun.com": ["section.article-body", "div.article-body", "article"],
    "www.biz.chosun.com": ["section.article-body", "div.article-body", "article"],
    "www.reuters.com": ["div.article-body__content__17Yit", "article", "div[data-testid='paragraph']"],
    "reuters.com": ["div.article-body__content__17Yit", "article", "div[data-testid='paragraph']"],
    "www.cnbc.com": ["div.ArticleBody-articleBody", "div.group", "article"],
    "cnbc.com": ["div.ArticleBody-articleBody", "div.group", "article"],
}


class ArticleExtractionError(RuntimeError):
    def __init__(self, message: str, code: str = "parse_failed") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class ArticleData:
    title: str
    url: str
    source: str
    published_at: str | None
    content: str
    image_url: str | None = None


def _decode_html_response(response: requests.Response) -> str:
    raw = response.content or b""
    if not raw:
        return ""

    candidates: list[str] = []
    if response.apparent_encoding:
        candidates.append(response.apparent_encoding)
    if response.encoding:
        candidates.append(response.encoding)
    candidates.extend(["utf-8", "cp949", "euc-kr"])

    seen: set[str] = set()
    for encoding in candidates:
        enc = str(encoding or "").strip().lower()
        if not enc or enc in seen:
            continue
        seen.add(enc)
        try:
            decoded = raw.decode(enc, errors="strict")
        except Exception:
            continue

        mojibake_score = decoded.count("ì") + decoded.count("ë") + decoded.count("ê") + decoded.count("ã")
        hangul_score = len(re.findall(r"[가-힣]", decoded))
        if hangul_score >= 20 or mojibake_score <= 3:
            return decoded

    return raw.decode("utf-8", errors="replace")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _text_from_element(element) -> str:
    if not element:
        return ""
    return _clean_text(element.get_text(" ", strip=True))


def _extract_title(soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "twitter:title"}),
        soup.find("h1"),
        soup.find("title"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if getattr(candidate, "name", None) == "meta":
            content = _clean_text(candidate.get("content", ""))
            if content:
                return content
        text = _text_from_element(candidate)
        if text:
            return text
    return "Untitled Article"


def _extract_image_url(soup: BeautifulSoup) -> str | None:
    candidates = [
        soup.find("meta", attrs={"property": "og:image"}),
        soup.find("meta", attrs={"name": "twitter:image"}),
    ]
    for node in candidates:
        if node and node.get("content"):
            return _clean_text(node.get("content"))
    return None


def _extract_published(soup: BeautifulSoup) -> str | None:
    keys = [
        ("property", "article:published_time"),
        ("name", "publish-date"),
        ("name", "pubdate"),
        ("itemprop", "datePublished"),
    ]
    for attr, key in keys:
        node = soup.find("meta", attrs={attr: key})
        if node and node.get("content"):
            return _clean_text(node.get("content"))
    return None


def _extract_content(url: str, soup: BeautifulSoup) -> str:
    hostname = urlparse(url).hostname or ""

    for selector in _SELECTORS_BY_DOMAIN.get(hostname.lower(), []):
        node = soup.select_one(selector)
        text = _text_from_element(node)
        if len(text) >= settings.min_article_chars:
            return text[: settings.max_article_chars]

    article_node = soup.find("article")
    article_text = _text_from_element(article_node)
    if len(article_text) >= settings.min_article_chars:
        return article_text[: settings.max_article_chars]

    paragraphs = [_text_from_element(p) for p in soup.find_all("p")]
    merged = _clean_text(" ".join(p for p in paragraphs if p))
    if len(merged) >= settings.min_article_chars:
        return merged[: settings.max_article_chars]

    raise ArticleExtractionError("본문 추출에 실패했습니다. 다른 URL을 시도해주세요.", code="parse_failed")


def fetch_article(url: str) -> ArticleData:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
    except Exception as exc:
        raise ArticleExtractionError(f"기사 페이지 요청 실패: {exc}", code="fetch_failed") from exc

    html = _decode_html_response(response)
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()

    content = _extract_content(url, soup)
    title = _extract_title(soup)
    image_url = _extract_image_url(soup)
    published_at = _extract_published(soup)
    source = (urlparse(url).hostname or "").replace("www.", "")

    return ArticleData(
        title=title,
        url=url,
        source=source,
        published_at=published_at,
        content=content,
        image_url=image_url,
    )
