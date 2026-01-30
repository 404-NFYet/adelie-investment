#!/usr/bin/env python3
"""
Ingest OpenDART "사업의 내용" tables into a Neo4j supply ontology graph.

Input: CSV with dart_corp_code (or corp_code), stock_code, corp_name (e.g. listed_companies_stock_dart.csv or dart_listed_companies.csv)
For each listed company:
  - Finds the most recent quarterly report (분기보고서) via OpenDART list.json (pblntf_ty=A)
  - Downloads the report XML via document.xml
  - Extracts from:
      Ⅱ. 사업의 내용 > 2. 주요 제품 및 서비스
      Ⅱ. 사업의 내용 > 3. 원재료 및 생산설비
  - Creates Company nodes and SUPPLIED_BY relationships.

Design:
  - Supplier companies are always represented as Company nodes and connected directly.
  - Relationship properties keep context (division/item/use/report date).

Run:
  docker compose --profile graph up -d neo4j
  OPENDART_API_KEY=... python3 backend-fastapi/scripts/opendart_supply_graph_neo4j.py \
    --input-csv corporate/data/dart_listed_companies.csv \
    --neo4j-http http://localhost:7474 --neo4j-user neo4j --neo4j-password password \
    --max-companies 999999
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


def _load_opendart_module() -> object:
    # Import the existing extractor script as a module (no package dependency).
    path = os.path.join(os.path.dirname(__file__), "opendart_bfs_ontology.py")
    spec = importlib.util.spec_from_file_location("opendart_bfs_ontology", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to import module from {path}")
    mod = importlib.util.module_from_spec(spec)
    # dataclasses (py3.13+) expects the module to exist in sys.modules during decoration.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _normalize_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = s.replace("㈜", "").replace("(주)", "").replace("주식회사", "").replace("유한회사", "")
    s = "".join(ch for ch in s if ch.isalnum() or ("가" <= ch <= "힣"))
    return s


def _company_id(corp_code: Optional[str], name: str) -> str:
    if corp_code:
        return corp_code
    h = hashlib.sha1(_normalize_name(name).encode("utf-8")).hexdigest()[:12]
    return f"ext:{h}"


def _concept_id(prefix: str, name: str) -> str:
    norm = _normalize_name(name)
    h = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{h}"


# [2026-02-04] Extended trivial/noise patterns for disclosure data quality
_TRIVIAL_VALUES = frozenset({
    "-", "—", "–", "·", "/",
    "기타", "소 계", "소계", "합 계", "합계", "총 계", "총계", "계",
    "해당없음", "해당 없음", "n/a", "없음", "미상", "불명",
    "사업부문", "품목", "용도", "주요거래처", "매입액", "매입처", "업체명",
    "상기 내용과 동일", "상기 참조", "주석 참조",
})
_MAX_MEANINGFUL_LEN = 200


def _is_trivial(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return True
    if len(v) <= 1:
        return True
    if len(v) > _MAX_MEANINGFUL_LEN:
        return True
    if v.lower() in _TRIVIAL_VALUES:
        return True
    # Number-only (amounts, counts mistakenly in text fields)
    if re.match(r"^\d+[,.\d]*\s*%?\s*$", v):
        return True
    return False


def validate_relationship(from_id: str, to_id: str, item: str) -> bool:
    """Filter self-loops and optional internal-trade rows."""
    if from_id == to_id:
        return False
    it = (item or "").strip()
    if "내부" in it or "계열사" in it:
        return False
    return True


@dataclass(frozen=True)
class ListedCompany:
    corp_code: str
    stock_code: str
    corp_name: str


def _normalize_corp_code(code: str) -> str:
    """Normalize corp_code to 8 digits (OpenDART format). Pad if short; strip leading zeros if >8."""
    s = (code or "").strip()
    if not s.isdigit():
        return s
    s = s.lstrip("0") or "0"
    if len(s) > 8:
        s = s[:8]
    return s.zfill(8)


def read_listed_companies(csv_path: str) -> List[ListedCompany]:
    out: List[ListedCompany] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Support both dart_corp_code (listed_companies_stock_dart) and corp_code (dart_listed_companies)
            corp_code = _normalize_corp_code(row.get("dart_corp_code") or row.get("corp_code") or "")
            stock_code = (row.get("stock_code") or "").strip()
            corp_name = (row.get("corp_name") or "").strip()
            if not corp_code or not corp_name:
                continue
            out.append(ListedCompany(corp_code=corp_code, stock_code=stock_code, corp_name=corp_name))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenDART -> Neo4j supply ontology ingest.")
    parser.add_argument("--api-key", default=os.environ.get("OPENDART_API_KEY") or "", help="OpenDART API key")
    parser.add_argument("--input-csv", default="listed_companies_stock_dart.csv", help="Input CSV path")
    parser.add_argument("--neo4j-http", default="http://localhost:7474", help="Neo4j HTTP base URL")
    parser.add_argument("--neo4j-user", default="neo4j", help="Neo4j user")
    parser.add_argument("--neo4j-password", default="password", help="Neo4j password (must match NEO4J_AUTH)")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N companies in the CSV (for chunking)")
    parser.add_argument("--max-companies", type=int, default=999999, help="Max number of companies to ingest (after offset)")
    parser.add_argument("--only-stock-codes", default="", help="Comma-separated 6-digit stock codes to ingest (optional)")
    parser.add_argument("--only-corp-codes", default="", help="Comma-separated DART corp codes to ingest (optional)")
    parser.add_argument("--since", default="20200101", help="Disclosure search start date (YYYYMMDD)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip companies already marked ingested=true")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Sleep N ms between companies (rate limiting)")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Missing OpenDART API key. Set OPENDART_API_KEY or pass --api-key.")

    mod = _load_opendart_module()
    corp_index = mod.load_corp_index(args.api_key)

    listed = read_listed_companies(args.input_csv)
    if args.only_stock_codes:
        allow = {s.strip() for s in args.only_stock_codes.split(",") if s.strip()}
        listed = [c for c in listed if c.stock_code in allow]
    if args.only_corp_codes:
        allow = {s.strip() for s in args.only_corp_codes.split(",") if s.strip()}
        listed = [c for c in listed if c.corp_code in allow]

    if args.offset > 0:
        listed = listed[args.offset :]
    listed = listed[: args.max_companies]

    def neo4j_commit(statement: str, parameters: dict) -> dict:
        url = urllib.parse.urljoin(args.neo4j_http.rstrip("/") + "/", "db/neo4j/tx/commit")
        payload = {"statements": [{"statement": statement, "parameters": parameters}]}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "narrative-ai-opendart-neo4j/1.0",
            },
            method="POST",
        )
        auth = f"{args.neo4j_user}:{args.neo4j_password}".encode("utf-8")
        req.add_header("Authorization", "Basic " + base64.b64encode(auth).decode("ascii"))
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        obj = json.loads(raw)
        if obj.get("errors"):
            raise RuntimeError(f"Neo4j error: {obj['errors'][0]}")
        return obj

    def run_write(cypher: str, params: dict) -> None:
        neo4j_commit(cypher, params)

    # Schema
    run_write("CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE", {})
    run_write("CREATE INDEX company_corp_code IF NOT EXISTS FOR (c:Company) ON (c.corp_code)", {})
    run_write("CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE", {})
    run_write("CREATE CONSTRAINT input_id IF NOT EXISTS FOR (i:Input) REQUIRE i.id IS UNIQUE", {})
    run_write("CREATE CONSTRAINT usecase_id IF NOT EXISTS FOR (u:UseCase) REQUIRE u.id IS UNIQUE", {})
    run_write("CREATE CONSTRAINT division_id IF NOT EXISTS FOR (d:Division) REQUIRE d.id IS UNIQUE", {})

    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()

    # Seed listed companies
    run_write(
        """
        UNWIND $rows AS row
        MERGE (c:Company {id: row.corp_code})
        SET c.corp_code = row.corp_code,
            c.stock_code = row.stock_code,
            c.name = row.corp_name,
            c.is_listed = true,
            c.updated_at = $now
        """,
        {"rows": [c.__dict__ for c in listed], "now": now},
    )

    ingest_count = 0
    rel_count = 0
    err_count = 0

    for idx, c in enumerate(listed, start=1):
        corp_code = c.corp_code
        print(f"[{idx}/{len(listed)}] ingest {c.corp_name} ({c.stock_code or '-'}) corp_code={corp_code}")

        if args.skip_existing:
            obj = neo4j_commit("MATCH (c:Company {id:$id}) RETURN c.ingested AS ingested", {"id": corp_code})
            recs = obj.get("results", [{}])[0].get("data", [])
            if recs and recs[0].get("row", [None])[0] is True:
                continue

        try:
            ex = mod.extract_company_sections(args.api_key, corp_code, corp_index, bgn_de=args.since)
        except Exception as e:
            err_count += 1
            print(f"  [warn] extract failed: {e}")
            run_write(
                "MATCH (c:Company {id:$id}) SET c.ingest_error=$err, c.updated_at=$now",
                {"id": corp_code, "err": str(e)[:2000], "now": now},
            )
            continue

        # Upsert company meta from DART index (cleaner corp_name, stock_code).
        run_write(
            """
            MATCH (c:Company {id:$id})
            SET c.name = $name,
                c.stock_code = coalesce($stock_code, c.stock_code),
                c.latest_quarter_rcept_no = $rcept_no,
                c.latest_quarter_rcept_dt = $rcept_dt,
                c.latest_quarter_report_nm = $report_nm,
                c.ingested = true,
                c.updated_at = $now
            """,
            {
                "id": corp_code,
                "name": ex.corp_name,
                "stock_code": ex.stock_code,
                "rcept_no": ex.rcept_no,
                "rcept_dt": ex.rcept_dt,
                "report_nm": ex.report_nm,
                "now": now,
            },
        )

        # Full ontology ingest:
        # - Company -> HAS_DIVISION -> Division
        # - Division -> PRODUCES -> Product
        # - Division -> PROCURES -> Input -> USED_FOR -> UseCase
        # - Company -> SUPPLIED_BY -> SupplierCompany (direct company-to-company BFS)
        # - SupplierCompany -> SUPPLIES_INPUT -> Input (detail linkage)
        supplier_nodes: Dict[str, dict] = {}
        division_nodes: Dict[str, dict] = {}
        product_nodes: Dict[str, dict] = {}
        input_nodes: Dict[str, dict] = {}
        use_nodes: Dict[str, dict] = {}

        has_division_rows: List[dict] = []
        produces_rows: List[dict] = []
        procures_rows: List[dict] = []
        input_use_rows: List[dict] = []
        supplies_input_rows: List[dict] = []
        supplied_by_rows: List[dict] = []

        # Products
        for pr in ex.products:
            division = (pr.division or "").strip()
            if _is_trivial(division):
                continue
            div_id = f"div:{corp_code}:{_normalize_name(division) or 'unknown'}"
            division_nodes.setdefault(div_id, {"id": div_id, "name": division, "corp_id": corp_code})
            has_division_rows.append({"corp_id": corp_code, "div_id": div_id})

            for prod in pr.products:
                if _is_trivial(prod):
                    continue
                pid = _concept_id("prod", prod)
                product_nodes.setdefault(pid, {"id": pid, "name": prod})
                produces_rows.append(
                    {
                        "div_id": div_id,
                        "prod_id": pid,
                        "rcept_no": ex.rcept_no,
                        "rcept_dt": ex.rcept_dt,
                    }
                )

        # Inputs / suppliers
        for inp in ex.inputs:
            division = (inp.division or "").strip()
            if _is_trivial(division):
                continue
            div_id = f"div:{corp_code}:{_normalize_name(division) or 'unknown'}"
            division_nodes.setdefault(div_id, {"id": div_id, "name": division, "corp_id": corp_code})
            has_division_rows.append({"corp_id": corp_code, "div_id": div_id})

            if _is_trivial(inp.item):
                continue
            input_id = _concept_id("in", inp.item)
            input_nodes.setdefault(input_id, {"id": input_id, "name": inp.item})
            procures_rows.append(
                {
                    "div_id": div_id,
                    "input_id": input_id,
                    "division": division,
                    "item": inp.item,
                    "rcept_no": ex.rcept_no,
                    "rcept_dt": ex.rcept_dt,
                }
            )

            if not _is_trivial(inp.use):
                use_id = _concept_id("use", inp.use)
                use_nodes.setdefault(use_id, {"id": use_id, "name": inp.use})
                input_use_rows.append({"input_id": input_id, "use_id": use_id})

            for sup in inp.suppliers:
                sid = _company_id(sup.corp_code, sup.name)
                if not validate_relationship(corp_code, sid, inp.item):
                    continue
                supplier_nodes.setdefault(
                    sid,
                    {
                        "id": sid,
                        "corp_code": sup.corp_code,
                        "stock_code": corp_index.stock_code_by_corp_code.get(sup.corp_code) if sup.corp_code else None,
                        "name": corp_index.corp_name_by_code.get(sup.corp_code) if sup.corp_code else sup.name,
                        "is_listed": False,
                    },
                )
                supplied_by_rows.append(
                    {
                        "from_id": corp_code,
                        "to_id": sid,
                        "division": division,
                        "item": inp.item,
                        "use": inp.use,
                        "rcept_no": ex.rcept_no,
                        "rcept_dt": ex.rcept_dt,
                    }
                )
                supplies_input_rows.append(
                    {
                        "supplier_id": sid,
                        "input_id": input_id,
                        "corp_id": corp_code,
                        "division": division,
                        "item": inp.item,
                        "use": inp.use,
                        "rcept_no": ex.rcept_no,
                        "rcept_dt": ex.rcept_dt,
                    }
                )

        if supplier_nodes:
            run_write(
                """
                UNWIND $rows AS row
                MERGE (s:Company {id: row.id})
                SET s.corp_code = row.corp_code,
                    s.stock_code = coalesce(row.stock_code, s.stock_code),
                    s.name = coalesce(row.name, s.name),
                    s.is_listed = coalesce(s.is_listed, row.is_listed),
                    s.updated_at = $now
                """,
                {"rows": list(supplier_nodes.values()), "now": now},
            )

        if division_nodes:
            run_write(
                """
                UNWIND $rows AS row
                MERGE (d:Division {id: row.id})
                SET d.name = row.name,
                    d.corp_id = row.corp_id,
                    d.updated_at = $now
                """,
                {"rows": list(division_nodes.values()), "now": now},
            )

        if product_nodes:
            run_write(
                """
                UNWIND $rows AS row
                MERGE (p:Product {id: row.id})
                SET p.name = row.name,
                    p.updated_at = $now
                """,
                {"rows": list(product_nodes.values()), "now": now},
            )

        if input_nodes:
            run_write(
                """
                UNWIND $rows AS row
                MERGE (i:Input {id: row.id})
                SET i.name = row.name,
                    i.updated_at = $now
                """,
                {"rows": list(input_nodes.values()), "now": now},
            )

        if use_nodes:
            run_write(
                """
                UNWIND $rows AS row
                MERGE (u:UseCase {id: row.id})
                SET u.name = row.name,
                    u.updated_at = $now
                """,
                {"rows": list(use_nodes.values()), "now": now},
            )

        if has_division_rows:
            run_write(
                """
                UNWIND $rows AS row
                MATCH (c:Company {id: row.corp_id})
                MATCH (d:Division {id: row.div_id})
                MERGE (c)-[:HAS_DIVISION]->(d)
                """,
                {"rows": has_division_rows},
            )

        if produces_rows:
            run_write(
                """
                UNWIND $rows AS row
                MATCH (d:Division {id: row.div_id})
                MATCH (p:Product {id: row.prod_id})
                MERGE (d)-[r:PRODUCES {prod_id: row.prod_id, rcept_no: row.rcept_no}]->(p)
                SET r.rcept_dt = row.rcept_dt,
                    r.updated_at = $now
                """,
                {"rows": produces_rows, "now": now},
            )

        if procures_rows:
            run_write(
                """
                UNWIND $rows AS row
                MATCH (d:Division {id: row.div_id})
                MATCH (i:Input {id: row.input_id})
                MERGE (d)-[r:PROCURES {input_id: row.input_id, rcept_no: row.rcept_no}]->(i)
                SET r.rcept_dt = row.rcept_dt,
                    r.division = row.division,
                    r.item = row.item,
                    r.updated_at = $now
                """,
                {"rows": procures_rows, "now": now},
            )

        if input_use_rows:
            run_write(
                """
                UNWIND $rows AS row
                MATCH (i:Input {id: row.input_id})
                MATCH (u:UseCase {id: row.use_id})
                MERGE (i)-[:USED_FOR]->(u)
                """,
                {"rows": input_use_rows},
            )

        if supplies_input_rows:
            run_write(
                """
                UNWIND $rows AS row
                MATCH (s:Company {id: row.supplier_id})
                MATCH (i:Input {id: row.input_id})
                MERGE (s)-[r:SUPPLIES_INPUT {input_id: row.input_id, rcept_no: row.rcept_no, corp_id: row.corp_id}]->(i)
                SET r.rcept_dt = row.rcept_dt,
                    r.division = row.division,
                    r.item = row.item,
                    r.use = row.use,
                    r.updated_at = $now
                """,
                {"rows": supplies_input_rows, "now": now},
            )

        if supplied_by_rows:
            run_write(
                """
                UNWIND $rows AS row
                MATCH (a:Company {id: row.from_id})
                MATCH (b:Company {id: row.to_id})
                MERGE (a)-[r:SUPPLIED_BY {
                  rcept_no: row.rcept_no,
                  division: row.division,
                  item: row.item,
                  use: row.use,
                  to_id: row.to_id
                }]->(b)
                SET r.rcept_dt = row.rcept_dt,
                    r.updated_at = $now
                """,
                {"rows": supplied_by_rows, "now": now},
            )

        ingest_count += 1
        rel_count += len(supplied_by_rows)
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    print(f"done. companies_ingested={ingest_count} relationships_created={rel_count} errors={err_count}")


if __name__ == "__main__":
    main()
