"""Diversity filter for keyword plans."""
from __future__ import annotations

import re
from typing import Iterable

from .types import KeywordPlan


def normalize_text(value: str) -> str:
    """Normalize text for comparison."""
    text = value.lower().strip()
    text = re.sub(r"^\[.*?\]\s*", "", text)
    text = re.sub(r"[\"'`]", "", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(value: str) -> set[str]:
    return {token for token in normalize_text(value).split(" ") if len(token) >= 2}


def _character_ngrams(value: str, n: int = 3) -> set[str]:
    compact = re.sub(r"\s+", "", normalize_text(value))
    return {compact[i : i + n] for i in range(0, max(0, len(compact) - n + 1))}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left.intersection(right))
    return intersection / (len(left) + len(right) - intersection)


def overlap_score(a: KeywordPlan, b: KeywordPlan) -> float:
    """Calculate overlap score between two keyword plans."""
    text_a = f"{a.keyword} {a.title} {a.context} {a.mirroring_hint}"
    text_b = f"{b.keyword} {b.title} {b.context} {b.mirroring_hint}"

    token_score = _jaccard(_tokenize(text_a), _tokenize(text_b))
    char_score = _jaccard(_character_ngrams(text_a), _character_ngrams(text_b))

    keyword_a = normalize_text(a.keyword)
    keyword_b = normalize_text(b.keyword)
    containment = 0.15 if keyword_a and keyword_b and (keyword_a in keyword_b or keyword_b in keyword_a) else 0.0

    return max(token_score, char_score) + containment


def sanitize_keyword_plans(plans: Iterable[KeywordPlan]) -> list[KeywordPlan]:
    """Sanitize and filter keyword plans."""
    output: list[KeywordPlan] = []
    for plan in plans:
        category = (plan.category or "Market trend").strip()
        domain = normalize_text(plan.domain or "macro").replace(" ", "_") or "macro"
        keyword = (plan.keyword or "").strip()
        title = (plan.title or "").strip()
        context = (plan.context or "").strip()
        hint = (plan.mirroring_hint or "").strip()

        if keyword and context:
            output.append(
                KeywordPlan(
                    category=category,
                    domain=domain,
                    keyword=keyword,
                    title=title,
                    context=context,
                    mirroring_hint=hint,
                )
            )
    return output


def pick_diverse_keyword_plans(plans: list[KeywordPlan], target_count: int) -> list[KeywordPlan]:
    """Pick diverse keyword plans to avoid redundancy.
    
    Args:
        plans: List of keyword plans to filter
        target_count: Target number of diverse plans to select
        
    Returns:
        List of diverse keyword plans
    """
    sanitized = sanitize_keyword_plans(plans)
    selected: list[KeywordPlan] = []

    used_keywords: set[str] = set()
    used_domains: set[str] = set()
    used_categories: set[str] = set()
    used_hints: set[str] = set()

    # Sort by context length (longer = more informative)
    sorted_plans = sorted(sanitized, key=lambda item: len(item.context), reverse=True)

    # First pass: strict diversity
    for plan in sorted_plans:
        if len(selected) >= target_count:
            break

        keyword = normalize_text(plan.keyword)
        domain = normalize_text(plan.domain)
        category = normalize_text(plan.category)
        hint = normalize_text(plan.mirroring_hint)

        if not keyword or keyword in used_keywords:
            continue
        if domain and domain in used_domains:
            continue
        if category and category in used_categories:
            continue
        if hint and hint in used_hints:
            continue
        if any(overlap_score(existing, plan) >= 0.45 for existing in selected):
            continue

        selected.append(plan)
        used_keywords.add(keyword)
        if domain:
            used_domains.add(domain)
        if category:
            used_categories.add(category)
        if hint:
            used_hints.add(hint)

    # Second pass: relaxed diversity if needed
    if len(selected) < target_count:
        for plan in sorted_plans:
            if len(selected) >= target_count:
                break
            keyword = normalize_text(plan.keyword)
            if not keyword or keyword in used_keywords:
                continue
            if any(overlap_score(existing, plan) >= 0.55 for existing in selected):
                continue

            selected.append(plan)
            used_keywords.add(keyword)

    return selected[:target_count]
