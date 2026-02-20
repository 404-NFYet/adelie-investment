from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import anyio
from openai import AsyncOpenAI

from app.core.cache import cache_backend
from app.core.config import settings
from app.services.article_service import ArticleData, ArticleExtractionError, fetch_article
from app.services.content_classifier import classify_finance_article
from app.services.upstream_client import upstream_client


class AnalyzeError(RuntimeError):
    def __init__(self, message: str, code: str = "ANALYZE_FAILED") -> None:
        super().__init__(message)
        self.code = code


_WORD_STOPLIST = {
    "기사",
    "시장",
    "내용",
    "이번",
    "관련",
    "전망",
    "발표",
    "분석",
    "경제",
    "뉴스",
    "ad",
    "구독",
    "클린뷰",
    "프린트",
}

_ALLOWED_ACRONYMS = {
    "AI",
    "GDP",
    "CPI",
    "PPI",
    "FOMC",
    "ETF",
    "PER",
    "PBR",
    "EPS",
    "ROE",
    "ROA",
    "EV",
    "EBITDA",
    "ADR",
    "IPO",
    "M&A",
}


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [c.strip() for c in chunks if c.strip()]


def _tokenize(text: str) -> list[str]:
    return [tok for tok in re.findall(r"[A-Za-z가-힣0-9]{2,}", text.lower()) if tok not in _WORD_STOPLIST]


def _korean_ratio(text: str) -> float:
    sample = str(text or "")[:3000]
    if not sample:
        return 0.0
    hangul = len(re.findall(r"[가-힣]", sample))
    alpha = len(re.findall(r"[A-Za-z]", sample))
    denom = hangul + alpha
    return (hangul / denom) if denom else 0.0


def _relevance_score(article_text: str, generated_text: str) -> float:
    article_tokens = set(_tokenize(article_text)[:3000])
    generated_tokens = set(_tokenize(generated_text))
    if not article_tokens or not generated_tokens:
        return 0.0
    overlap = len(article_tokens & generated_tokens)
    return overlap / max(len(generated_tokens), 1)


def _extract_concepts(text: str) -> list[str]:
    candidates: list[str] = []

    for term in re.findall(r"\b[A-Z]{2,10}\b", text):
        if term.lower() in _WORD_STOPLIST:
            continue
        if term not in _ALLOWED_ACRONYMS:
            continue
        if term not in candidates:
            candidates.append(term)

    finance_terms = [
        "코스피",
        "코스닥",
        "주가",
        "증시",
        "금리",
        "환율",
        "인플레이션",
        "실적",
        "매출",
        "영업이익",
        "배당",
        "수익률",
        "채권",
        "연준",
        "달러",
    ]
    for term in finance_terms:
        if term in text and term not in candidates:
            candidates.append(term)

    return candidates[:10]


def _is_bad_term(term: str, kind: str) -> bool:
    cleaned = re.sub(r"\s+", " ", term.strip())
    if not cleaned:
        return True
    if cleaned.lower() in _WORD_STOPLIST:
        return True
    if re.fullmatch(r"[\d\W_]+", cleaned):
        return True

    symbol_ratio = len(re.findall(r"[^0-9A-Za-z가-힣\s\-·]", cleaned)) / max(len(cleaned), 1)
    if symbol_ratio > 0.25:
        return True

    if kind == "word":
        if " " in cleaned:
            return True
        if len(cleaned) < 2 or len(cleaned) > 24:
            return True

    if kind == "phrase":
        if len(cleaned) < 5 or len(cleaned) > 56:
            return True
        if len(cleaned.split()) == 1 and len(cleaned) < 8:
            return True

    return False


def _normalize_glossary_item(raw: Any, kind: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    term = re.sub(r"\s+", " ", str(raw.get("term", "")).strip())
    definition = re.sub(r"\s+", " ", str(raw.get("definition", "")).strip())
    if not term or not definition:
        return None
    if _is_bad_term(term, kind):
        return None

    importance = raw.get("importance", 3)
    try:
        importance = int(importance)
    except (TypeError, ValueError):
        importance = 3
    importance = max(1, min(5, importance))

    return {
        "term": term,
        "definition": definition,
        "kind": kind,
        "importance": importance,
    }


def _dedupe_and_sort(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        key = str(item["term"]).strip().lower()
        prev = merged.get(key)
        if prev is None or int(item.get("importance", 1)) > int(prev.get("importance", 1)):
            merged[key] = item
    values = list(merged.values())
    values.sort(key=lambda x: (-int(x.get("importance", 1)), -len(str(x.get("term", "")))))
    return values


def _fallback_words(text: str) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for term in _extract_concepts(text):
        if _is_bad_term(term, "word"):
            continue
        words.append(
            {
                "term": term,
                "definition": f"{term}는 이 기사에서 핵심적으로 등장하는 금융 용어입니다.",
                "kind": "word",
                "importance": 3,
            }
        )
    return words


def _fallback_phrases(text: str) -> list[dict[str, Any]]:
    phrases: list[dict[str, Any]] = []
    for sentence in _split_sentences(text):
        sentence = sentence.strip(" .")
        if len(sentence) < 10 or len(sentence) > 58:
            continue
        if _is_bad_term(sentence, "phrase"):
            continue
        phrases.append(
            {
                "term": sentence,
                "definition": "기사 맥락을 이해하는 데 중요한 구절입니다.",
                "kind": "phrase",
                "importance": 2,
            }
        )
        if len(phrases) >= 8:
            break
    return phrases


def _normalize_glossary(payload: dict[str, Any], fallback_text: str) -> list[dict[str, Any]]:
    glossary_raw = payload.get("glossary")
    words: list[dict[str, Any]] = []
    phrases: list[dict[str, Any]] = []

    if isinstance(glossary_raw, dict):
        for item in glossary_raw.get("words", []) or []:
            normalized = _normalize_glossary_item(item, "word")
            if normalized:
                words.append(normalized)
        for item in glossary_raw.get("phrases", []) or []:
            normalized = _normalize_glossary_item(item, "phrase")
            if normalized:
                phrases.append(normalized)

    if not words:
        words = _fallback_words(fallback_text)
    if not phrases:
        phrases = _fallback_phrases(fallback_text)

    return _dedupe_and_sort(phrases)[:6] + _dedupe_and_sort(words)[:6]


def _word_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    if re.fullmatch(r"[0-9A-Za-z가-힣]+", term):
        josa = r"(?:은|는|이|가|을|를|와|과|의|에|도|로|으로|에서|에게|께|보다|까지|부터|만|조차)?"
        return re.compile(rf"(?<![0-9A-Za-z가-힣])({escaped})(?={josa}(?![0-9A-Za-z가-힣]))", flags=re.IGNORECASE)
    return re.compile(escaped, flags=re.IGNORECASE)


def _build_marked_text(text: str, glossary: list[dict[str, Any]]) -> str:
    rendered = str(text or "")
    if not rendered:
        return rendered

    phrases = sorted([g for g in glossary if g.get("kind") == "phrase"], key=lambda x: len(str(x.get("term", ""))), reverse=True)
    words = sorted([g for g in glossary if g.get("kind") == "word"], key=lambda x: len(str(x.get("term", ""))), reverse=True)
    ordered = phrases + words

    replacements: dict[str, str] = {}
    hit = 0
    for entry in ordered:
        term = str(entry.get("term", "")).strip()
        kind = str(entry.get("kind", "word"))
        if not term:
            continue

        pattern = re.compile(re.escape(term), flags=re.IGNORECASE) if kind == "phrase" else _word_pattern(term)
        match = pattern.search(rendered)
        if not match:
            continue

        token = f"@@H{hit}@@"
        matched = match.group(1) if match.lastindex else match.group(0)
        safe_term = term.replace("'", "&#39;").replace('"', "&quot;")
        replacements[token] = f"<mark class='term-highlight' data-term='{safe_term}' data-kind='{kind}'>{matched}</mark>"
        rendered = f"{rendered[:match.start()]}{token}{rendered[match.end():]}"
        hit += 1

    for token, markup in replacements.items():
        rendered = rendered.replace(token, markup)
    return rendered


def _heuristic_payload(article: ArticleData) -> dict[str, Any]:
    sentences = _split_sentences(article.content)
    background = " ".join(sentences[:2]) or article.content[:240]
    importance = " ".join(sentences[2:4]) or "시장 참여자 심리에 영향을 줄 수 있는 이슈입니다."
    takeaways = [
        sentences[0] if len(sentences) > 0 else "핵심 이슈를 먼저 확인하세요.",
        sentences[1] if len(sentences) > 1 else "수치의 방향성과 속도를 함께 보세요.",
        sentences[2] if len(sentences) > 2 else "관련 산업 파급 효과를 분리해서 보세요.",
    ]

    concepts = _extract_concepts(f"{article.title} {article.content}")
    related = [w for w in re.split(r"\s+", article.title) if len(w) >= 2][:5]

    regenerated_article = " ".join(sentences[:8]) or article.content[:1400]
    explain_text = " ".join(sentences[:5]) or article.content[:1000]

    return {
        "korean_title": article.title,
        "regenerated_article": regenerated_article,
        "explain_text": explain_text,
        "newsletter": {
            "background": background,
            "importance": importance,
            "concepts": concepts,
            "related": related,
            "takeaways": takeaways,
        },
        "glossary": {
            "words": [{"term": c, "definition": f"{c} 핵심 금융 개념", "importance": 3} for c in concepts[:6]],
            "phrases": [],
        },
    }


async def _call_llm(client: AsyncOpenAI, prompt: str) -> dict[str, Any] | None:
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 금융 뉴스 교육 콘텐츠 편집자다. 원문 근거 문장에 기반해 사실만 요약한다. "
                        "질문형 문장, 근거 없는 확장, 마크다운 문법 사용을 금지한다. 반드시 JSON만 반환한다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=1300,
            temperature=0.15,
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if not isinstance(data.get("newsletter"), dict):
            return None
        if not isinstance(data.get("explain_text"), str):
            return None
        if not isinstance(data.get("korean_title"), str):
            data["korean_title"] = ""
        if not isinstance(data.get("regenerated_article"), str):
            data["regenerated_article"] = data.get("explain_text", "")
        if not isinstance(data.get("glossary"), dict):
            data["glossary"] = {"words": [], "phrases": []}
        return data
    except Exception:
        return None


async def _llm_payload(article: ArticleData, difficulty: str, market: str) -> dict[str, Any] | None:
    if not settings.openai_api_key:
        return None

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = (
        "다음 금융 기사 원문을 한국어 학습용 요약으로 재구성해 JSON으로만 응답하세요.\n"
        "원문 근거가 없는 문장, 질문형 문장, 일반 상식 확장, 마크다운 기호(###, -, *)를 금지합니다.\n"
        "필수 키:\n"
        "- korean_title(string)\n"
        "- regenerated_article(string)\n"
        "- explain_text(string)\n"
        "- newsletter(object)\n"
        "- glossary(object)\n"
        "newsletter 키: background(string), importance(string), concepts(string[]), related(string[]), takeaways(string[]).\n"
        "glossary 키:\n"
        "- words: [{term, definition, importance(1~5)}], 최대 6\n"
        "- phrases: [{term, definition, importance(1~5)}], 최대 6\n"
        "words에는 금융 용어만 넣고, phrases에는 기사 핵심 구절만 넣으세요.\n"
        f"difficulty={difficulty}, market={market}\n\n"
        f"제목: {article.title}\n"
        f"출처: {article.source}\n"
        f"본문:\n{article.content[:8000]}"
    )

    data = await _call_llm(client, prompt)
    if not data:
        return None

    combined = f"{data.get('korean_title', '')} {data.get('regenerated_article', '')} {data.get('explain_text', '')}"
    if _korean_ratio(combined) < 0.12:
        return None
    return data


def _render_newsletter_text(newsletter: dict[str, Any]) -> str:
    concepts = ", ".join(newsletter.get("concepts", [])[:6])
    related = ", ".join(newsletter.get("related", [])[:6])
    takeaways = " / ".join(newsletter.get("takeaways", [])[:5])

    return (
        f"배경: {newsletter.get('background', '')}\n"
        f"왜 중요한가: {newsletter.get('importance', '')}\n"
        f"핵심 개념: {concepts}\n"
        f"관련 이슈: {related}\n"
        f"핵심 정리: {takeaways}"
    )


def _merge_terms(*term_lists: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for term_list in term_lists:
        for item in term_list or []:
            term = str(item.get("term", "")).strip()
            if not term:
                continue
            key = term.lower()
            prev = merged.get(key)
            if prev is None or int(item.get("importance", 1)) > int(prev.get("importance", 1)):
                merged[key] = item
    return _dedupe_and_sort(list(merged.values()))


async def _merge_upstream_glossary(glossary: list[dict[str, Any]], content: str, difficulty: str) -> list[dict[str, Any]]:
    if not content:
        return glossary

    try:
        _, highlighted_terms = await upstream_client.highlight_content(content=content, difficulty=difficulty, custom_terms=[])
    except Exception:
        return glossary

    extra: list[dict[str, Any]] = []
    for item in highlighted_terms or []:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        if not term:
            continue
        kind = "word" if " " not in term else "phrase"
        normalized = _normalize_glossary_item(
            {
                "term": term,
                "definition": str(item.get("definition") or item.get("description") or "핵심 표현"),
                "importance": item.get("importance", 2),
            },
            kind,
        )
        if normalized:
            extra.append(normalized)

    words = [g for g in glossary if g.get("kind") == "word"] + [g for g in extra if g.get("kind") == "word"]
    phrases = [g for g in glossary if g.get("kind") == "phrase"] + [g for g in extra if g.get("kind") == "phrase"]
    return _dedupe_and_sort(phrases)[:6] + _dedupe_and_sort(words)[:6]


def _extract_numeric_evidence(text: str) -> list[str]:
    patterns = [
        r"\b\d+(?:\.\d+)?%",
        r"\b\d+(?:\.\d+)?\s*(?:bp|bps)",
        r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*(?:원|달러|조|억|만)",
        r"\b\d+(?:\.\d+)?\s*(?:원|달러|조|억|만)",
        r"\b\d{4}(?:\.\d+)?\s*(?:포인트|p)",
    ]

    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text, flags=re.IGNORECASE))

    cleaned = []
    seen = set()
    for item in found:
        key = item.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item.strip())
    return cleaned


async def analyze_url(url: str, difficulty: str, market: str) -> dict[str, Any]:
    cache_key = hashlib.sha256(f"{url}|{difficulty}|{market}".encode("utf-8")).hexdigest()
    cached = await cache_backend.get_json(cache_key)
    if cached:
        cached["cached"] = True
        return cached

    try:
        article = await anyio.to_thread.run_sync(fetch_article, url)
    except ArticleExtractionError as exc:
        raise AnalyzeError(str(exc), code=getattr(exc, "code", "CONTENT_EXTRACTION_FAILED")) from exc

    if article.content_quality_score < 45:
        raise AnalyzeError("본문 품질이 낮아 분석할 수 없습니다. 다른 기사 URL을 시도해주세요.", code="LOW_CONTENT_QUALITY")

    finance_cls = classify_finance_article(article.title, article.content, article.source)
    if not finance_cls.is_finance_article:
        raise AnalyzeError("금융 기사만 분석할 수 있습니다. 금융/경제 기사 URL을 입력해주세요.", code="NON_FINANCE_ARTICLE")

    llm_data = await _llm_payload(article, difficulty, market)
    payload = llm_data or _heuristic_payload(article)

    generated_combo = " ".join(
        [
            str(payload.get("regenerated_article", "")),
            str(payload.get("explain_text", "")),
            str(payload.get("newsletter", {}).get("background", "")),
            str(payload.get("newsletter", {}).get("importance", "")),
        ]
    )
    if _relevance_score(article.content, generated_combo) < 0.12:
        payload = _heuristic_payload(article)

    newsletter = payload.get("newsletter", {})
    explain_text = str(payload.get("explain_text", "")).strip() or article.content[:1200]
    regenerated_article = str(payload.get("regenerated_article", "")).strip() or explain_text
    article_title = str(payload.get("korean_title", "")).strip() or article.title

    glossary = _normalize_glossary(payload, f"{article.content}\n{regenerated_article}\n{explain_text}")
    glossary = await _merge_upstream_glossary(glossary, f"{regenerated_article}\n{explain_text}", difficulty)

    explain_base = f"재구성 본문: {regenerated_article}\n\n이해를 돕는 해설: {explain_text}"
    newsletter_text = _render_newsletter_text(newsletter)

    explain_marked = _build_marked_text(explain_base, glossary)
    newsletter_marked = _build_marked_text(newsletter_text, glossary)

    evidence = _extract_numeric_evidence(f"{article.content}\n{newsletter_text}")
    chart_ready = len(evidence) >= 2
    chart_reason = None if chart_ready else "기사에서 신뢰 가능한 수치 근거를 충분히 찾지 못했습니다."

    result = {
        "article": {
            "title": article_title,
            "url": article.url,
            "source": article.source,
            "published_at": article.published_at,
            "content": article.content,
            "image_url": article.image_url,
        },
        "explain_mode": {
            "content_marked": explain_marked,
            "highlighted_terms": glossary,
            "glossary": glossary,
        },
        "newsletter_mode": {
            "background": str(newsletter.get("background", "")).strip(),
            "importance": str(newsletter.get("importance", "")).strip(),
            "concepts": [str(x) for x in (newsletter.get("concepts", []) or [])][:6],
            "related": [str(x) for x in (newsletter.get("related", []) or [])][:6],
            "takeaways": [str(x) for x in (newsletter.get("takeaways", []) or [])][:5],
            "content_marked": newsletter_marked,
            "highlighted_terms": glossary,
            "glossary": glossary,
        },
        "highlighted_terms": _merge_terms(glossary),
        "glossary": glossary,
        "fetch_status": "ok",
        "cached": False,
        "content_quality_score": article.content_quality_score,
        "quality_flags": article.quality_flags,
        "article_domain": article.article_domain,
        "is_finance_article": True,
        "chart_ready": chart_ready,
        "chart_unavailable_reason": chart_reason,
    }

    await cache_backend.set_json(cache_key, result)
    return result
