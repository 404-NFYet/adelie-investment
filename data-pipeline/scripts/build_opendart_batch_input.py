#!/usr/bin/env python3
"""
# [2026-02-04] OpenDART Batch API 입력 JSONL 생성
data/opendart_xml/ 내 XML 파일을 읽어 OpenAI Batch API용 JSONL 생성.
예외 감지(빈 XML, 비공개 문구, 지주회사 등) 옵션 지원.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Script dir for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opendart_batch_extract_prompt import get_system_prompt, get_user_prompt

# 정보 비공개 감지 패턴 (예외 처리용)
CONFIDENTIAL_PATTERNS = [
    re.compile(r"보안유지.*기재하지", re.IGNORECASE),
    re.compile(r"영업비밀.*생략", re.IGNORECASE),
    re.compile(r"특정.*업체.*명시.*않", re.IGNORECASE),
    re.compile(r"다수의.*거래처.*구축", re.IGNORECASE),
]

HOLDING_COMPANY_PATTERN = re.compile(r"순수\s*지주\s*회사.*제품.*없습니다", re.IGNORECASE)

# XML 루트 속성 파싱용
ROOT_ATTR_PATTERN = re.compile(
    r'<OPENDART_SECTIONS\s+rcept_no="([^"]*)"\s+rcept_dt="([^"]*)"',
    re.IGNORECASE,
)


def _read_xml_meta_and_content(path: str, max_chars: int) -> tuple[str, str, str, str]:
    """Read XML file; return (corp_code, rcept_no, rcept_dt, content).
    content is truncated to max_chars.
    """
    corp_code = os.path.splitext(os.path.basename(path))[0]
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    rcept_no = ""
    rcept_dt = ""
    m = ROOT_ATTR_PATTERN.search(raw)
    if m:
        rcept_no, rcept_dt = m.group(1), m.group(2)
    content = raw
    if max_chars > 0 and len(content) > max_chars:
        content = content[:max_chars] + "\n\n... (truncated)"
    return corp_code, rcept_no, rcept_dt, content


def detect_exceptions(content: str) -> dict[str, bool]:
    """Pre-scan content for exception hints (for logging/skip options)."""
    lines = content.splitlines()
    line_count = len(lines)
    has_section2 = "SECTION-2" in content or "<SECTION-2" in content
    has_products_title = "주요 제품" in content or "Main products" in content
    has_materials_title = "원재료" in content or "Raw materials" in content

    empty_xml = line_count < 20 or (line_count < 50 and not has_section2)
    no_products_section = not has_products_title
    no_materials_section = not has_materials_title
    holding_company = bool(HOLDING_COMPANY_PATTERN.search(content))
    supplier_confidential = any(p.search(content) for p in CONFIDENTIAL_PATTERNS)

    return {
        "empty_xml": empty_xml,
        "no_products_section": no_products_section,
        "no_materials_section": no_materials_section,
        "holding_company": holding_company,
        "supplier_confidential": supplier_confidential,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build OpenAI Batch API input JSONL from OpenDART XMLs")
    parser.add_argument(
        "--xml-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "data", "opendart_xml"),
        help="Directory containing corp_code.xml files",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "..", "data", "opendart_batch_input.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--detect-exceptions",
        action="store_true",
        help="Run exception detection (log/skip empty or trivial files)",
    )
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Do not emit requests for files detected as empty_xml (requires --detect-exceptions)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=120_000,
        help="Max XML characters per request (0 = no limit). Default 120000 to fit context.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model name to embed in request body",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of XML files to process (0 = all)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.xml_dir):
        print(f"Error: xml-dir not found: {args.xml_dir}", file=sys.stderr)
        sys.exit(1)

    xml_files = sorted(
        [f for f in os.listdir(args.xml_dir) if f.endswith(".xml") and not f.startswith(".")]
    )
    if args.limit > 0:
        xml_files = xml_files[: args.limit]

    system_prompt = get_system_prompt()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    skipped = 0
    written = 0

    with open(args.output, "w", encoding="utf-8") as out:
        for i, fn in enumerate(xml_files):
            path = os.path.join(args.xml_dir, fn)
            if not os.path.isfile(path):
                continue
            try:
                corp_code, rcept_no, rcept_dt, content = _read_xml_meta_and_content(
                    path, args.max_chars
                )
            except Exception as e:
                print(f"Warning: skip {fn}: {e}", file=sys.stderr)
                skipped += 1
                continue

            if args.detect_exceptions:
                ex = detect_exceptions(content)
                if args.skip_empty and ex.get("empty_xml"):
                    skipped += 1
                    continue

            user_prompt = get_user_prompt(corp_code, rcept_no, rcept_dt, content)
            body = {
                "model": args.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            }
            record = {
                "custom_id": corp_code,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": body,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"Wrote {written} requests to {args.output}", file=sys.stderr)
    if skipped:
        print(f"Skipped {skipped} files", file=sys.stderr)


if __name__ == "__main__":
    main()
