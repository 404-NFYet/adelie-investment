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
    "www.hankyung.com": ["div#articletxt", "div.article-body", "div#contents", "div.article_txt"],
    "hankyung.com": ["div#articletxt", "div.article-body", "div#contents", "div.article_txt"],
    "www.mk.co.kr": ["div#article_body", "div.article_body", "div#articleBody", "div#content"],
    "mk.co.kr": ["div#article_body", "div.article_body", "div#articleBody", "div#content"],
    "www.asiae.co.kr": ["div#txt_area", "div.news_area", "div#articleBody"],
    "asiae.co.kr": ["div#txt_area", "div.news_area", "div#articleBody"],
    "www.marketwatch.com": ["div.article__body", "article.article__body", "div#article-body"],
    "marketwatch.com": ["div.article__body", "article.article__body", "div#article-body"],
    "biz.chosun.com": ["section.article-body", "div.article-body", "article"],
    "www.biz.chosun.com": ["section.article-body", "div.article-body", "article"],
    "www.reuters.com": ["article", "div[data-testid='paragraph']"],
    "reuters.com": ["article", "div[data-testid='paragraph']"],
    "www.cnbc.com": ["div.ArticleBody-articleBody", "div.group", "article"],
    "cnbc.com": ["div.ArticleBody-articleBody", "div.group", "article"],
}

_GENERIC_CONTENT_SELECTORS = [
    "article",
    "main article",
    "main",
    "div[itemprop='articleBody']",
    "section[itemprop='articleBody']",
    "div[class*='article-body']",
    "div[class*='article_body']",
    "section[class*='article-body']",
]

_NOISE_KEYWORDS = {
    "구독",
    "글자크기",
    "글자크기 설정",
    "기사 스크랩",
    "클린뷰",
    "프린트",
    "공유",
    "댓글",
    "추천 기사",
    "TOP",
    "top",
    "저작권",
    "무단전재",
    "재배포",
    "광고",
    "입력",
    "수정",
}

_NOISE_PATTERNS = [
    re.compile(r"(?:기자|특파원)\s+[\w\.\-]+@[\w\-\.]+", re.IGNORECASE),
    re.compile(r"\b[\w\.\-]+@[\w\-\.]+\.[A-Za-z]{2,}\b"),
    re.compile(r"저작권자\s*©?.*"),
    re.compile(r"무단전재\s*및\s*재배포\s*금지"),
    re.compile(r"구독(?:하기)?"),
    re.compile(r"기사\s*스크랩"),
    re.compile(r"글자\s*크기\s*조절"),
    re.compile(r"글자\s*크기\s*설정"),
    re.compile(r"클린뷰"),
    re.compile(r"프린트"),
    re.compile(r"공유"),
    re.compile(r"댓글\s*\d*"),
    re.compile(r"추천\s*기사"),
    re.compile(r"\bTOP\b", re.IGNORECASE),
    re.compile(r"(?:\b가\b\s*){3,}"),
    re.compile(r"\b(?:입력|수정)\s*\d{4}[./-]\d{1,2}[./-]\d{1,2}"),
]


class ArticleExtractionError(RuntimeError):
    def __init__(self, message: str, code: str = "CONTENT_EXTRACTION_FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class ArticleData:
    title: str
    url: str
    source: str
    published_at: str | None
    content: str
    image_url: str | None
    article_domain: str
    content_quality_score: int
    quality_flags: list[str]


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
        text = _clean_text(candidate.get_text(" ", strip=True))
        if text:
            return text
    return "Untitled Article"


def _extract_image_url(soup: BeautifulSoup) -> str | None:
    for key, value in [("property", "og:image"), ("name", "twitter:image")]:
        node = soup.find("meta", attrs={key: value})
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


def _remove_noise_nodes(soup: BeautifulSoup) -> None:
    for tag in ["script", "style", "noscript", "header", "footer", "nav", "aside", "form", "button"]:
        for node in soup.find_all(tag):
            node.decompose()

    noisy = soup.find_all(
        attrs={
            "class": re.compile(r"comment|share|subscribe|ad|banner|copyright|toolbar|util|btn", re.IGNORECASE)
        }
    )
    noisy.extend(
        soup.find_all(attrs={"id": re.compile(r"comment|share|subscribe|ad|banner|copyright|toolbar|util", re.IGNORECASE)})
    )
    for node in noisy:
        node.decompose()


def _normalize_lines(raw_text: str) -> str:
    lines = [line.strip() for line in re.split(r"\n+", raw_text) if line.strip()]
    cleaned: list[str] = []
    seen: set[str] = set()

    for line in lines:
        line_compact = _clean_text(line)
        if len(line_compact) < 5:
            continue

        if any(pattern.search(line_compact) for pattern in _NOISE_PATTERNS):
            continue

        keyword_hits = sum(1 for kw in _NOISE_KEYWORDS if kw in line_compact)
        if keyword_hits >= 2:
            continue

        key = line_compact.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(line_compact)

    return _clean_text(" ".join(cleaned))


def _score_candidate(text: str) -> float:
    if not text:
        return -999.0

    length = len(text)
    sentence_count = len(re.findall(r"[.!?다요]\s", text))
    link_like = len(re.findall(r"https?://|www\.|@[\w\-\.]+", text))
    boilerplate_hits = sum(text.count(keyword) for keyword in _NOISE_KEYWORDS)

    length_score = min(length / 1800.0, 1.0) * 45.0
    sentence_score = min(sentence_count / 16.0, 1.0) * 35.0
    penalty = min(link_like * 6 + boilerplate_hits * 2.5, 55.0)

    return length_score + sentence_score - penalty


def _collect_candidates(url: str, soup: BeautifulSoup) -> list[str]:
    hostname = (urlparse(url).hostname or "").lower()
    selectors = _SELECTORS_BY_DOMAIN.get(hostname, []) + _GENERIC_CONTENT_SELECTORS

    candidates: list[str] = []
    seen: set[str] = set()
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        text = _normalize_lines(node.get_text("\n", strip=True))
        if len(text) < settings.min_article_chars:
            continue
        key = text[:300].lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(text[: settings.max_article_chars])

    paragraphs = [_clean_text(p.get_text(" ", strip=True)) for p in soup.find_all("p")]
    merged = _normalize_lines("\n".join([p for p in paragraphs if p]))
    if len(merged) >= settings.min_article_chars:
        candidates.append(merged[: settings.max_article_chars])

    return candidates


def evaluate_content_quality(text: str) -> tuple[int, list[str]]:
    value = _clean_text(text)
    flags: list[str] = []

    if not value:
        return 0, ["empty_content"]

    length = len(value)
    sentence_count = max(1, len(re.findall(r"[.!?다요]\s", value)))
    boilerplate_hits = sum(value.count(keyword) for keyword in _NOISE_KEYWORDS)
    email_hits = len(re.findall(r"\b[\w\.\-]+@[\w\-\.]+\.[A-Za-z]{2,}\b", value))

    score = 100
    if length < 500:
        score -= 35
        flags.append("too_short")
    elif length < 900:
        score -= 15
        flags.append("short_content")

    if sentence_count < 5:
        score -= 25
        flags.append("low_sentence_count")

    if boilerplate_hits >= 3:
        score -= 30
        flags.append("boilerplate_heavy")

    if email_hits > 0:
        score -= 20
        flags.append("contains_contact")

    unique_ratio = len(set(value.split())) / max(len(value.split()), 1)
    if unique_ratio < 0.32:
        score -= 15
        flags.append("repetitive_text")

    score = max(0, min(100, score))
    return score, flags


def _extract_content(url: str, soup: BeautifulSoup) -> tuple[str, int, list[str]]:
    candidates = _collect_candidates(url, soup)
    if not candidates:
        raise ArticleExtractionError("본문 후보를 찾지 못했습니다. 다른 URL을 시도해주세요.", code="CONTENT_EXTRACTION_FAILED")

    best = max(candidates, key=_score_candidate)
    best = best[: settings.max_article_chars]

    score, flags = evaluate_content_quality(best)
    if score < 45:
        raise ArticleExtractionError(
            "본문 품질이 낮아 분석을 중단했습니다. 다른 금융 기사 URL을 시도해주세요.",
            code="LOW_CONTENT_QUALITY",
        )

    return best, score, flags


def fetch_article(url: str) -> ArticleData:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
    except Exception as exc:
        raise ArticleExtractionError(f"기사 페이지 요청 실패: {exc}", code="CONTENT_EXTRACTION_FAILED") from exc

    html = _decode_html_response(response)
    soup = BeautifulSoup(html, "html.parser")
    _remove_noise_nodes(soup)

    content, quality_score, quality_flags = _extract_content(url, soup)
    title = _extract_title(soup)
    image_url = _extract_image_url(soup)
    published_at = _extract_published(soup)
    domain = (urlparse(url).hostname or "").replace("www.", "")

    return ArticleData(
        title=title,
        url=url,
        source=domain,
        published_at=published_at,
        content=content,
        image_url=image_url,
        article_domain=domain,
        content_quality_score=quality_score,
        quality_flags=quality_flags,
    )
