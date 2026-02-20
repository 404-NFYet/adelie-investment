from __future__ import annotations

import re
from dataclasses import dataclass


FINANCE_KEYWORDS = {
    "코스피",
    "코스닥",
    "증시",
    "주가",
    "환율",
    "금리",
    "채권",
    "연준",
    "fed",
    "cpi",
    "ppi",
    "gdp",
    "실적",
    "매출",
    "영업이익",
    "배당",
    "투자",
    "etf",
    "나스닥",
    "다우",
    "인플레이션",
    "물가",
    "달러",
    "원화",
    "시총",
    "공매도",
    "수익률",
    "유가",
}

POLITICAL_OR_GENERAL_KEYWORDS = {
    "민주당",
    "국민의힘",
    "대통령",
    "총선",
    "복당",
    "국회",
    "검찰",
    "재판",
    "장관",
    "법안",
    "여야",
    "정치",
    "선거",
    "외교",
}


@dataclass
class FinanceClassification:
    is_finance_article: bool
    score: int
    matched_finance: list[str]
    matched_non_finance: list[str]


def _collect_matches(text: str, candidates: set[str]) -> list[str]:
    lowered = text.lower()
    matched: list[str] = []
    for keyword in candidates:
        kw = keyword.lower()
        if kw in lowered:
            matched.append(keyword)
    return sorted(set(matched))


def classify_finance_article(title: str, content: str, source: str = "") -> FinanceClassification:
    sample = f"{title}\n{content[:4000]}"
    finance = _collect_matches(sample, FINANCE_KEYWORDS)
    non_finance = _collect_matches(sample, POLITICAL_OR_GENERAL_KEYWORDS)

    number_hits = len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:%|bp|bps|원|달러|조|억|만)\b", sample, flags=re.IGNORECASE))

    score = len(finance) * 2 + min(number_hits, 3) - len(non_finance) * 2

    # Financial media bias (slight positive only)
    source_l = source.lower()
    if any(token in source_l for token in ["hankyung", "mk.co.kr", "chosun", "marketwatch", "reuters", "cnbc"]):
        score += 1

    is_finance = score >= 3 and len(finance) >= 2
    return FinanceClassification(
        is_finance_article=is_finance,
        score=score,
        matched_finance=finance,
        matched_non_finance=non_finance,
    )
