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
from app.services.upstream_client import upstream_client


class AnalyzeError(RuntimeError):
    pass


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
}


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [c.strip() for c in chunks if c.strip()]


def _extract_concepts(text: str) -> list[str]:
    candidates: list[str] = []

    upper_terms = re.findall(r"\b[A-Z]{2,10}\b", text)
    for term in upper_terms:
        if term not in candidates:
            candidates.append(term)

    kr_terms = [
        "금리",
        "인플레이션",
        "환율",
        "실적",
        "매출",
        "영업이익",
        "배당",
        "변동성",
        "유동성",
        "경기",
        "관세",
        "주가",
        "신용카드",
        "소비",
    ]
    for term in kr_terms:
        if term in text and term not in candidates:
            candidates.append(term)

    return candidates[:10]


def _korean_ratio(text: str) -> float:
    sample = str(text or "")[:3000]
    if not sample:
        return 0.0
    hangul = len(re.findall(r"[가-힣]", sample))
    alpha = len(re.findall(r"[A-Za-z]", sample))
    denom = hangul + alpha
    if denom == 0:
        return 0.0
    return hangul / denom


def _is_probably_english(text: str) -> bool:
    sample = text[:2500]
    if not sample:
        return False
    alpha = re.findall(r"[A-Za-z]", sample)
    hangul = re.findall(r"[가-힣]", sample)
    return len(alpha) > (len(hangul) * 2 + 40)


def _is_bad_term(term: str, kind: str) -> bool:
    cleaned = re.sub(r"\s+", " ", term.strip())
    if not cleaned:
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
        if cleaned.lower() in _WORD_STOPLIST:
            return True

    if kind == "phrase":
        if len(cleaned) < 4 or len(cleaned) > 48:
            return True
        if len(cleaned.split()) == 1 and len(cleaned) < 6:
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
    except (ValueError, TypeError):
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
        item = {
            "term": term,
            "definition": f"{term}는 이 기사에서 이해해야 할 핵심 금융 용어입니다.",
            "kind": "word",
            "importance": 3,
        }
        if not _is_bad_term(term, "word"):
            words.append(item)
    return words


def _fallback_phrases(text: str) -> list[dict[str, Any]]:
    phrases: list[dict[str, Any]] = []
    for sentence in _split_sentences(text):
        sentence = sentence.strip(" .")
        if len(sentence) < 8 or len(sentence) > 50:
            continue
        item = {
            "term": sentence,
            "definition": "기사의 맥락을 이해하는 데 중요한 구절입니다.",
            "kind": "phrase",
            "importance": 2,
        }
        if not _is_bad_term(sentence, "phrase"):
            phrases.append(item)
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

    words = _dedupe_and_sort(words)[:6]
    phrases = _dedupe_and_sort(phrases)[:6]
    return phrases + words


def _word_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    if re.fullmatch(r"[0-9A-Za-z가-힣]+", term):
        josa = "(?:은|는|이|가|을|를|와|과|의|에|도|로|으로|에서|에게|께|보다|까지|부터|만|조차)?"
        return re.compile(
            rf"(?<![0-9A-Za-z가-힣])({escaped})(?={josa}(?![0-9A-Za-z가-힣]))",
            flags=re.IGNORECASE,
        )
    return re.compile(escaped, flags=re.IGNORECASE)


def _build_marked_text(text: str, glossary: list[dict[str, Any]]) -> str:
    rendered = str(text or "")
    if not rendered:
        return rendered

    phrases = sorted(
        [g for g in glossary if g.get("kind") == "phrase"],
        key=lambda x: len(str(x.get("term", ""))),
        reverse=True,
    )
    words = sorted(
        [g for g in glossary if g.get("kind") == "word"],
        key=lambda x: len(str(x.get("term", ""))),
        reverse=True,
    )
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
        replacements[token] = (
            f"<mark class='term-highlight' data-term='{safe_term}' data-kind='{kind}'>{matched}</mark>"
        )
        rendered = f"{rendered[:match.start()]}{token}{rendered[match.end():]}"
        hit += 1

    for token, markup in replacements.items():
        rendered = rendered.replace(token, markup)

    return rendered


def _heuristic_payload(article: ArticleData) -> dict[str, Any]:
    sentences = _split_sentences(article.content)
    background = " ".join(sentences[:2]) or article.content[:240]
    importance = " ".join(sentences[2:4]) or "시장 참여자 심리에 직접 영향을 주는 이슈로 보입니다."
    takeaways = [
        sentences[0] if len(sentences) > 0 else "핵심 이슈를 먼저 확인하세요.",
        sentences[1] if len(sentences) > 1 else "수치 변화의 방향성과 속도를 함께 보세요.",
        sentences[2] if len(sentences) > 2 else "관련 업종/종목 파급효과를 분리해 보세요.",
    ]

    title_words = [w for w in re.split(r"\s+", article.title) if len(w) >= 2]
    related = title_words[:5]

    concepts = _extract_concepts(article.title + " " + article.content)
    explain_text = " ".join(sentences[:5]) or article.content[:1000]
    regenerated_article = " ".join(sentences[:8]) or article.content[:1400]

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
            "words": [{"term": c, "definition": f"{c} 관련 핵심 개념입니다.", "importance": 3} for c in concepts[:6]],
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
                        "당신은 금융 뉴스 품질 편집자다. 핵심 팩트는 유지하고, 한국어로 명확하게 재구성한다. "
                        "반드시 JSON만 반환한다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=1300,
            temperature=0.2,
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
    base_prompt = (
        "다음 기사 원문을 한국어 교육 콘텐츠로 재구성해 JSON으로만 답해주세요.\n"
        "영문 기사여도 결과 텍스트는 반드시 자연스러운 한국어여야 합니다.\n"
        "요구 키:\n"
        "- korean_title(string)\n"
        "- regenerated_article(string)\n"
        "- explain_text(string)\n"
        "- newsletter(object)\n"
        "- glossary(object)\n"
        "newsletter 키: background(string), importance(string), concepts(string[]), related(string[]), takeaways(string[]).\n"
        "glossary 키:\n"
        "- words: [{term, definition, importance(1~5)}] // 어려운 용어(단어), 최대 6개\n"
        "- phrases: [{term, definition, importance(1~5)}] // 중요한 구절(구 단위), 최대 6개\n"
        "phrases의 term은 4~20자 핵심 표현으로 뽑고, words의 term은 단어형으로 뽑으세요.\n"
        "difficultly와 market을 참고해 쉬운 한국어로 작성하세요.\n"
        f"difficulty={difficulty}, market={market}\n\n"
        f"제목: {article.title}\n"
        f"출처: {article.source}\n"
        f"본문:\n{article.content[:8000]}"
    )

    data = await _call_llm(client, base_prompt)
    if not data:
        return None

    combined = f"{data.get('korean_title', '')} {data.get('regenerated_article', '')} {data.get('explain_text', '')}"
    if _korean_ratio(combined) >= 0.15:
        return data

    retry_prompt = (
        base_prompt
        + "\n\n중요: 이전 응답의 한국어 비율이 부족했다. 모든 텍스트를 한국어 문장으로 다시 작성하라. "
        "영문 단어는 괄호 안 보조 표기만 허용한다."
    )
    retried = await _call_llm(client, retry_prompt)
    return retried or data


def _render_newsletter_text(newsletter: dict[str, Any]) -> str:
    concepts = newsletter.get("concepts", []) or []
    related = newsletter.get("related", []) or []
    takeaways = newsletter.get("takeaways", []) or []

    concept_lines = "\n".join(f"- {item}" for item in concepts[:6]) or "- 해당 기사에서 핵심 개념을 추출하지 못했습니다."
    related_lines = "\n".join(f"- {item}" for item in related[:6]) or "- 관련 이슈를 추출하지 못했습니다."
    takeaway_lines = "\n".join(f"- {item}" for item in takeaways[:5]) or "- 핵심 체크포인트를 추출하지 못했습니다."

    return (
        f"### 배경\n{newsletter.get('background', '')}\n\n"
        f"### 왜 중요한가\n{newsletter.get('importance', '')}\n\n"
        "### 핵심 개념\n"
        f"{concept_lines}\n\n"
        "### 관련 이슈\n"
        f"{related_lines}\n\n"
        "### 핵심 정리\n"
        f"{takeaway_lines}"
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


async def _merge_upstream_glossary(
    glossary: list[dict[str, Any]],
    content: str,
    difficulty: str,
) -> list[dict[str, Any]]:
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
        definition = str(item.get("definition") or item.get("description") or "핵심 맥락에서 자주 등장하는 표현입니다.").strip()
        normalized = _normalize_glossary_item(
            {
                "term": term,
                "definition": definition,
                "importance": item.get("importance", 2),
            },
            kind,
        )
        if normalized:
            extra.append(normalized)

    words = [g for g in glossary if g.get("kind") == "word"] + [g for g in extra if g.get("kind") == "word"]
    phrases = [g for g in glossary if g.get("kind") == "phrase"] + [g for g in extra if g.get("kind") == "phrase"]

    return _dedupe_and_sort(phrases)[:6] + _dedupe_and_sort(words)[:6]


def _coerce_payload_to_korean(payload: dict[str, Any], article: ArticleData) -> dict[str, Any]:
    base = dict(payload)
    title = str(base.get("korean_title", "")).strip() or article.title
    explain_text = str(base.get("explain_text", "")).strip()
    regen = str(base.get("regenerated_article", "")).strip() or explain_text

    combined = f"{title} {regen} {explain_text}"
    if _korean_ratio(combined) >= 0.12:
        base["korean_title"] = title
        if not base.get("regenerated_article"):
            base["regenerated_article"] = regen
        return base

    fallback = _heuristic_payload(article)
    fallback["korean_title"] = f"[번역 요약] {title}" if title else article.title
    if isinstance(base.get("newsletter"), dict):
        fallback["newsletter"] = base["newsletter"]
    return fallback


async def analyze_url(url: str, difficulty: str, market: str) -> dict[str, Any]:
    cache_key = hashlib.sha256(f"{url}|{difficulty}|{market}".encode("utf-8")).hexdigest()
    cached = await cache_backend.get_json(cache_key)
    if cached:
        cached["cached"] = True
        return cached

    try:
        article = await anyio.to_thread.run_sync(fetch_article, url)
    except ArticleExtractionError as exc:
        raise AnalyzeError(str(exc)) from exc

    llm_data = await _llm_payload(article, difficulty, market)
    payload = _coerce_payload_to_korean(llm_data or _heuristic_payload(article), article)

    newsletter = payload.get("newsletter", {})
    explain_text = str(payload.get("explain_text", "")).strip() or article.content[:1200]
    regenerated_article = str(payload.get("regenerated_article", "")).strip() or explain_text

    glossary = _normalize_glossary(payload, f"{regenerated_article}\n{explain_text}")
    glossary = await _merge_upstream_glossary(glossary, f"{regenerated_article}\n{explain_text}", difficulty)

    article_title = str(payload.get("korean_title", "")).strip() or article.title
    if _is_probably_english(article_title + " " + explain_text):
        article_title = f"[번역 요약] {article_title}"

    explain_base = (
        "### 재구성 본문\n"
        f"{regenerated_article}\n\n"
        "### 이해를 돕는 해설\n"
        f"{explain_text}"
    )

    newsletter_text = _render_newsletter_text(newsletter)
    explain_marked = _build_marked_text(explain_base, glossary)
    newsletter_marked = _build_marked_text(newsletter_text, glossary)

    explain_terms = glossary
    newsletter_terms = glossary

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
            "highlighted_terms": explain_terms,
            "glossary": glossary,
        },
        "newsletter_mode": {
            "background": str(newsletter.get("background", "")).strip(),
            "importance": str(newsletter.get("importance", "")).strip(),
            "concepts": [str(x) for x in (newsletter.get("concepts", []) or [])][:6],
            "related": [str(x) for x in (newsletter.get("related", []) or [])][:6],
            "takeaways": [str(x) for x in (newsletter.get("takeaways", []) or [])][:5],
            "content_marked": newsletter_marked,
            "highlighted_terms": newsletter_terms,
            "glossary": glossary,
        },
        "highlighted_terms": _merge_terms(explain_terms, newsletter_terms),
        "glossary": glossary,
        "fetch_status": "ok",
        "cached": False,
    }

    await cache_backend.set_json(cache_key, result)
    return result
