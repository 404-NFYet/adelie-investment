#!/usr/bin/env python3
"""Load OpenDART batch extract JSONL into Neo4j. Requires: pip install neo4j."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opendart_utils import normalize_company


def _load_corp_name_map(csv_path: str) -> dict[str, str]:
    """Load corp_code -> corp_name mapping from CSV."""
    mapping: dict[str, str] = {}
    if not csv_path or not os.path.isfile(csv_path):
        return mapping
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            corp_code = (row.get("dart_corp_code") or row.get("corp_code") or "").strip()
            corp_name = (row.get("corp_name") or "").strip()
            if corp_code and corp_name:
                # Normalize corp_code to 8 digits
                if corp_code.isdigit():
                    corp_code = corp_code.lstrip("0").zfill(8)
                mapping[corp_code] = normalize_company(corp_name)
    return mapping

_TRIVIAL = frozenset({
    "-", "—", "·", "/", "기타", "소계", "합계", "계", "해당없음", "없음", "미상", "n/a",
    "사업부문", "품목", "용도", "주요거래처", "매입액", "매입처",
})


def _is_trivial(s: str) -> bool:
    if not s or not isinstance(s, str):
        return True
    t = s.strip()
    if not t or len(t) <= 1:
        return True
    if t.lower() in _TRIVIAL:
        return True
    if re.match(r"^\d+[,.\d]*\s*%?\s*$", t):
        return True
    return False


def _norm_for_id(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\(주\)|주식회사|㈜|유한회사", "", s, flags=re.IGNORECASE)
    return "".join(c for c in s if c.isalnum() or ("가" <= c <= "힣"))


def _company_id(corp_code: str | None, name: str) -> str:
    if corp_code:
        return corp_code
    h = hashlib.sha1(_norm_for_id(name).encode("utf-8")).hexdigest()[:12]
    return f"ext:{h}"


def _concept_id(prefix: str, name: str) -> str:
    h = hashlib.sha1(_norm_for_id(name).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{h}"


def _parse_batch_output_line(line: str) -> tuple[str, dict] | None:
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    custom_id = obj.get("custom_id") or ""
    res = obj.get("response") or {}
    body = res.get("body") or {}
    choices = body.get("choices") or []
    if not choices:
        return None
    content = (choices[0].get("message") or {}).get("content") or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {}
    return (custom_id, data)


def _collect_nodes_edges(corp_code: str, data: dict, corp_name_map: dict[str, str] | None = None) -> tuple[list, list, list, list, list]:
    # Get company name from mapping, fallback to corp_code
    corp_name = (corp_name_map or {}).get(corp_code, corp_code)
    companies = [{"id": corp_code, "corp_code": corp_code, "name": corp_name, "is_listed": True}]
    products, materials, segments, rels = [], [], [], []
    ex = data.get("exceptions") or {}
    if ex.get("empty_xml") or ex.get("holding_company"):
        return companies, products, materials, segments, rels
    for p in data.get("products") or []:
        name = (p.get("item_name") or "").strip()
        if _is_trivial(name):
            continue
        pid = _concept_id("prod", name)
        products.append({"id": pid, "name": name})
        rels.append({"type": "PRODUCES", "from_id": corp_code, "to_id": pid})
    for m in data.get("materials") or []:
        name = (m.get("item_name") or "").strip()
        if _is_trivial(name):
            continue
        mid = _concept_id("mat", name)
        materials.append({"id": mid, "name": name})
        rels.append({"type": "PROCURES", "from_id": corp_code, "to_id": mid})
    for s in data.get("suppliers") or []:
        name = (s.get("name") or "").strip()
        if _is_trivial(name):
            continue
        sid = _company_id(None, name)
        companies.append({"id": sid, "corp_code": None, "name": normalize_company(name), "is_listed": False})
        rels.append({"type": "SUPPLIED_BY", "from_id": corp_code, "to_id": sid})
    for c in data.get("customers") or []:
        name = (c.get("name") or "").strip()
        if _is_trivial(name):
            continue
        cid = _company_id(None, name)
        companies.append({"id": cid, "corp_code": None, "name": normalize_company(name), "is_listed": False})
        rels.append({"type": "SELLS_TO", "from_id": corp_code, "to_id": cid})
    for sub in data.get("subsidiaries") or []:
        name = (sub.get("name") or "").strip()
        if _is_trivial(name):
            continue
        sid = _company_id(None, name)
        companies.append({"id": sid, "corp_code": None, "name": normalize_company(name), "is_listed": False})
        rels.append({"type": "OWNS", "from_id": corp_code, "to_id": sid})
    for seg in data.get("business_segments") or []:
        name = (seg.get("segment_name") or "").strip()
        if _is_trivial(name):
            continue
        seg_id = f"seg:{corp_code}:{_concept_id('s', name)}"
        segments.append({"id": seg_id, "name": name, "corp_id": corp_code, "main_goods": seg.get("main_goods_services"), "sales_amount": seg.get("sales_amount")})
        rels.append({"type": "OPERATES", "from_id": corp_code, "to_id": seg_id})
    return companies, products, materials, segments, rels


def main() -> None:
    parser = argparse.ArgumentParser(description="Load OpenDART batch extract results into Neo4j")
    parser.add_argument("--input", required=True, help="Batch output JSONL path")
    parser.add_argument("--corp-csv", default=os.path.join(os.path.dirname(__file__), "..", "..", "corporate", "data", "listed_companies_stock_dart.csv"), help="CSV with corp_code->corp_name mapping")
    parser.add_argument("--neo4j-uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--neo4j-user", default=os.environ.get("NEO4J_USER", "neo4j"))
    parser.add_argument("--neo4j-password", default=os.environ.get("NEO4J_PASSWORD", "password"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not os.path.isfile(args.input):
        print(f"Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    # Load corp_code -> corp_name mapping
    corp_name_map = _load_corp_name_map(args.corp_csv)
    print(f"Loaded {len(corp_name_map)} corp_code->name mappings from {args.corp_csv}", file=sys.stderr)
    records: list[tuple[str, dict]] = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            parsed = _parse_batch_output_line(line)
            if parsed:
                records.append(parsed)
            if args.limit > 0 and len(records) >= args.limit:
                break
    print(f"Parsed {len(records)} batch result(s)", file=sys.stderr)
    if args.dry_run:
        for corp_code, data in records[:3]:
            c, p, m, seg, r = _collect_nodes_edges(corp_code, data, corp_name_map)
            corp_name = corp_name_map.get(corp_code, corp_code)
            print(f"  {corp_code} ({corp_name}): companies={len(c)} products={len(p)} materials={len(m)} segments={len(seg)} rels={len(r)}", file=sys.stderr)
        return
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("Install neo4j: pip install neo4j", file=sys.stderr)
        sys.exit(1)
    driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, args.neo4j_password))

    def run(cypher: str, params: dict) -> None:
        with driver.session() as session:
            session.run(cypher, params)

    run("CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE", {})
    run("CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE", {})
    run("CREATE CONSTRAINT material_id IF NOT EXISTS FOR (m:Material) REQUIRE m.id IS UNIQUE", {})
    run("CREATE CONSTRAINT segment_id IF NOT EXISTS FOR (s:BusinessSegment) REQUIRE s.id IS UNIQUE", {})
    total_c = total_p = total_m = total_s = total_r = err = 0
    for corp_code, data in records:
        try:
            companies, products, materials, segments, rels = _collect_nodes_edges(corp_code, data, corp_name_map)
        except Exception as e:
            print(f"  [warn] {corp_code}: {e}", file=sys.stderr)
            err += 1
            continue
        company_map = {x["id"]: x for x in companies}
        companies = list(company_map.values())
        if companies:
            run("UNWIND $rows AS row MERGE (c:Company {id: row.id}) SET c.corp_code = row.corp_code, c.name = coalesce(row.name, c.name), c.is_listed = coalesce(row.is_listed, false)", {"rows": companies})
            total_c += len(companies)
        if products:
            run("UNWIND $rows AS row MERGE (p:Product {id: row.id}) SET p.name = row.name", {"rows": products})
            total_p += len(products)
        if materials:
            run("UNWIND $rows AS row MERGE (m:Material {id: row.id}) SET m.name = row.name", {"rows": materials})
            total_m += len(materials)
        if segments:
            run("UNWIND $rows AS row MERGE (s:BusinessSegment {id: row.id}) SET s.name = row.name, s.corp_id = row.corp_id, s.main_goods = row.main_goods, s.sales_amount = row.sales_amount", {"rows": segments})
            total_s += len(segments)
        for r in rels:
            typ, from_id, to_id = r["type"], r["from_id"], r["to_id"]
            if typ == "PRODUCES":
                run("MATCH (a:Company {id: $f}) MATCH (b:Product {id: $t}) MERGE (a)-[:PRODUCES]->(b)", {"f": from_id, "t": to_id})
            elif typ == "PROCURES":
                run("MATCH (a:Company {id: $f}) MATCH (b:Material {id: $t}) MERGE (a)-[:PROCURES]->(b)", {"f": from_id, "t": to_id})
            elif typ == "SUPPLIED_BY":
                run("MATCH (a:Company {id: $f}) MATCH (b:Company {id: $t}) MERGE (a)-[:SUPPLIED_BY]->(b)", {"f": from_id, "t": to_id})
            elif typ == "SELLS_TO":
                run("MATCH (a:Company {id: $f}) MATCH (b:Company {id: $t}) MERGE (a)-[:SELLS_TO]->(b)", {"f": from_id, "t": to_id})
            elif typ == "OWNS":
                run("MATCH (a:Company {id: $f}) MATCH (b:Company {id: $t}) MERGE (a)-[:OWNS]->(b)", {"f": from_id, "t": to_id})
            elif typ == "OPERATES":
                run("MATCH (a:Company {id: $f}) MATCH (b:BusinessSegment {id: $t}) MERGE (a)-[:OPERATES]->(b)", {"f": from_id, "t": to_id})
            total_r += 1
    driver.close()
    print(f"Done. companies={total_c} products={total_p} materials={total_m} segments={total_s} rels={total_r} errors={err}")


if __name__ == "__main__":
    main()
