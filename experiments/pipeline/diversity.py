"""다양성 필터 (Diversity Gate) - 실험용.

키워드 플랜 간 중복을 감지하고 다양한 테마를 선별한다.
자카드 유사도 + 문자 n-gram + 키워드 포함관계를 종합 평가.
"""

from __future__ import annotations

import re

from pipeline.types import KeywordPlan


def _normalize_text(value: str) -> str:
    """텍스트 정규화: 소문자, 특수문자 제거."""
    text = value.lower().strip()
    text = re.sub(r"^\[.*?\]\s*", "", text)
    text = re.sub(r"[\"'`]", "", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(value: str) -> set[str]:
    """텍스트를 2자 이상 토큰으로 분리."""
    return {token for token in _normalize_text(value).split(" ") if len(token) >= 2}


def _character_ngrams(value: str, n: int = 3) -> set[str]:
    """문자 n-gram 생성."""
    compact = re.sub(r"\s+", "", _normalize_text(value))
    return {compact[i : i + n] for i in range(max(0, len(compact) - n + 1))}


def _jaccard(left: set[str], right: set[str]) -> float:
    """자카드 유사도 계산."""
    if not left or not right:
        return 0.0
    intersection = len(left.intersection(right))
    return intersection / (len(left) + len(right) - intersection)


def _overlap_score(a: KeywordPlan, b: KeywordPlan) -> float:
    """두 키워드 플랜 간 중복 점수 계산."""
    text_a = f"{a.keyword} {a.title} {a.context} {a.mirroring_hint}"
    text_b = f"{b.keyword} {b.title} {b.context} {b.mirroring_hint}"

    token_score = _jaccard(_tokenize(text_a), _tokenize(text_b))
    char_score = _jaccard(_character_ngrams(text_a), _character_ngrams(text_b))

    keyword_a = _normalize_text(a.keyword)
    keyword_b = _normalize_text(b.keyword)
    containment = (
        0.15
        if keyword_a and keyword_b and (keyword_a in keyword_b or keyword_b in keyword_a)
        else 0.0
    )

    return max(token_score, char_score) + containment


def pick_diverse_keyword_plans(
    plans: list[KeywordPlan],
    target_count: int,
) -> list[KeywordPlan]:
    """다양성 필터를 적용하여 키워드 플랜 선택.

    1차: 키워드/도메인/카테고리/힌트 중복 없이 엄격 선택
    2차: 부족한 경우 유사도 임계값만으로 완화 선택
    """
    sanitized = [p for p in plans if p.keyword.strip() and p.context.strip()]
    selected: list[KeywordPlan] = []

    used_keywords: set[str] = set()
    used_domains: set[str] = set()
    used_categories: set[str] = set()
    used_hints: set[str] = set()

    # 컨텍스트가 긴(정보 풍부한) 항목 우선
    sorted_plans = sorted(sanitized, key=lambda item: len(item.context), reverse=True)

    # 1차: 엄격한 다양성 필터
    for plan in sorted_plans:
        if len(selected) >= target_count:
            break

        keyword = _normalize_text(plan.keyword)
        domain = _normalize_text(plan.domain)
        category = _normalize_text(plan.category)
        hint = _normalize_text(plan.mirroring_hint)

        if not keyword or keyword in used_keywords:
            continue
        if domain and domain in used_domains:
            continue
        if category and category in used_categories:
            continue
        if hint and hint in used_hints:
            continue
        if any(_overlap_score(existing, plan) >= 0.45 for existing in selected):
            continue

        selected.append(plan)
        used_keywords.add(keyword)
        if domain:
            used_domains.add(domain)
        if category:
            used_categories.add(category)
        if hint:
            used_hints.add(hint)

    # 2차: 완화된 필터
    if len(selected) < target_count:
        for plan in sorted_plans:
            if len(selected) >= target_count:
                break
            keyword = _normalize_text(plan.keyword)
            if not keyword or keyword in used_keywords:
                continue
            if any(_overlap_score(existing, plan) >= 0.55 for existing in selected):
                continue
            selected.append(plan)
            used_keywords.add(keyword)

    return selected[:target_count]
