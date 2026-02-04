#!/usr/bin/env python3
"""
# [2026-02-06] OpenDART 배치 추출 공통 유틸리티
회사명 정규화 등 Batch 추출 및 Neo4j 연동에서 공통 사용.
Copied from narrative-ai for narrative-investment.
"""

from __future__ import annotations

import re


def normalize_company(name: str) -> str:
    """회사명 정규화: (주), 주식회사 제거, 공백 정리. 영문/숫자는 유지."""
    if not name or not isinstance(name, str):
        return ""
    s = name.strip()
    s = re.sub(r"\(주\)|주식회사|\(株\)|㈜|유한회사", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_company_for_match(name: str) -> str:
    """매칭용 정규화: normalize_company 후 소문자·공백 제거 (동일 회사 판별용)."""
    s = normalize_company(name)
    s = s.lower()
    s = re.sub(r"[^0-9a-z가-힣]", "", s)
    return s
