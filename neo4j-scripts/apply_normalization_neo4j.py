#!/usr/bin/env python3
"""
Apply canonical mapping to Neo4j nodes.
Updates node names and merges duplicates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def load_mapping(path: str) -> dict:
    """Load canonical mapping from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def apply_company_normalization(driver, mapping: dict[str, str], dry_run: bool = False) -> int:
    """Apply company name normalization to Neo4j."""
    if not mapping:
        return 0
    
    # Convert to list of {original, canonical} for Cypher
    mappings_list = [
        {'original': orig, 'canonical': canon}
        for orig, canon in mapping.items()
        if orig != canon  # Only include if actually changed
    ]
    
    if not mappings_list:
        return 0
    
    if dry_run:
        print(f"  [DRY RUN] Would update {len(mappings_list)} company names", file=sys.stderr)
        return len(mappings_list)
    
    # Update names
    with driver.session() as session:
        result = session.run("""
            UNWIND $mappings AS m
            MATCH (c:Company {name: m.original})
            SET c.original_name = c.name, c.name = m.canonical
            RETURN count(c) AS updated
        """, {'mappings': mappings_list})
        updated = result.single()['updated']
    
    return updated


def apply_product_normalization(driver, mapping: dict[str, str], dry_run: bool = False) -> int:
    """Apply product name normalization to Neo4j."""
    if not mapping:
        return 0
    
    mappings_list = [
        {'original': orig, 'canonical': canon}
        for orig, canon in mapping.items()
        if orig != canon
    ]
    
    if not mappings_list:
        return 0
    
    if dry_run:
        print(f"  [DRY RUN] Would update {len(mappings_list)} product names", file=sys.stderr)
        return len(mappings_list)
    
    with driver.session() as session:
        result = session.run("""
            UNWIND $mappings AS m
            MATCH (p:Product {name: m.original})
            SET p.original_name = p.name, p.name = m.canonical
            RETURN count(p) AS updated
        """, {'mappings': mappings_list})
        updated = result.single()['updated']
    
    return updated


def apply_material_normalization(driver, mapping: dict[str, str], dry_run: bool = False) -> int:
    """Apply material name normalization to Neo4j."""
    if not mapping:
        return 0
    
    mappings_list = [
        {'original': orig, 'canonical': canon}
        for orig, canon in mapping.items()
        if orig != canon
    ]
    
    if not mappings_list:
        return 0
    
    if dry_run:
        print(f"  [DRY RUN] Would update {len(mappings_list)} material names", file=sys.stderr)
        return len(mappings_list)
    
    with driver.session() as session:
        result = session.run("""
            UNWIND $mappings AS m
            MATCH (mat:Material {name: m.original})
            SET mat.original_name = mat.name, mat.name = m.canonical
            RETURN count(mat) AS updated
        """, {'mappings': mappings_list})
        updated = result.single()['updated']
    
    return updated


def apply_segment_normalization(driver, mapping: dict[str, str], dry_run: bool = False) -> int:
    """Apply segment name normalization to Neo4j."""
    if not mapping:
        return 0
    
    mappings_list = [
        {'original': orig, 'canonical': canon}
        for orig, canon in mapping.items()
        if orig != canon
    ]
    
    if not mappings_list:
        return 0
    
    if dry_run:
        print(f"  [DRY RUN] Would update {len(mappings_list)} segment names", file=sys.stderr)
        return len(mappings_list)
    
    with driver.session() as session:
        result = session.run("""
            UNWIND $mappings AS m
            MATCH (s:BusinessSegment {name: m.original})
            SET s.original_name = s.name, s.name = m.canonical
            RETURN count(s) AS updated
        """, {'mappings': mappings_list})
        updated = result.single()['updated']
    
    return updated


def merge_duplicate_companies(driver, dry_run: bool = False) -> int:
    """Merge Company nodes with the same canonical name."""
    if dry_run:
        # Count potential merges
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Company)
                WITH c.name AS name, count(c) AS cnt
                WHERE cnt > 1
                RETURN sum(cnt - 1) AS duplicates
            """)
            duplicates = result.single()['duplicates'] or 0
        print(f"  [DRY RUN] Would merge {duplicates} duplicate company nodes", file=sys.stderr)
        return duplicates
    
    # Merge duplicates - keep the one with corp_code, merge relationships
    with driver.session() as session:
        # First, find duplicates
        result = session.run("""
            MATCH (c:Company)
            WITH c.name AS name, collect(c) AS nodes
            WHERE size(nodes) > 1
            RETURN name, nodes
        """)
        
        merged = 0
        for record in result:
            nodes = record['nodes']
            if len(nodes) < 2:
                continue
            
            # Keep the node with corp_code if any, otherwise first
            keep = nodes[0]
            for node in nodes:
                if node.get('corp_code'):
                    keep = node
                    break
            
            # Merge others into keep
            for node in nodes:
                if node.element_id == keep.element_id:
                    continue
                
                # Transfer relationships
                session.run("""
                    MATCH (old:Company) WHERE elementId(old) = $old_id
                    MATCH (keep:Company) WHERE elementId(keep) = $keep_id
                    
                    // Transfer outgoing relationships
                    CALL {
                        WITH old, keep
                        MATCH (old)-[r]->(target)
                        WHERE NOT (keep)-[:SUPPLIED_BY|SELLS_TO|PRODUCES|PROCURES|OWNS|OPERATES]->(target)
                        CREATE (keep)-[r2:MERGED_REL]->(target)
                        SET r2 = properties(r)
                        DELETE r
                    }
                    
                    // Transfer incoming relationships
                    CALL {
                        WITH old, keep
                        MATCH (source)-[r]->(old)
                        WHERE NOT (source)-[:SUPPLIED_BY|SELLS_TO|PRODUCES|PROCURES|OWNS|OPERATES]->(keep)
                        CREATE (source)-[r2:MERGED_REL]->(keep)
                        SET r2 = properties(r)
                        DELETE r
                    }
                    
                    // Delete old node
                    DETACH DELETE old
                """, {'old_id': node.element_id, 'keep_id': keep.element_id})
                merged += 1
        
        return merged


def merge_duplicate_products(driver, dry_run: bool = False) -> int:
    """Merge Product nodes with the same canonical name."""
    if dry_run:
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Product)
                WITH p.name AS name, count(p) AS cnt
                WHERE cnt > 1
                RETURN sum(cnt - 1) AS duplicates
            """)
            duplicates = result.single()['duplicates'] or 0
        print(f"  [DRY RUN] Would merge {duplicates} duplicate product nodes", file=sys.stderr)
        return duplicates
    
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Product)
            WITH p.name AS name, collect(p) AS nodes
            WHERE size(nodes) > 1
            UNWIND range(1, size(nodes)-1) AS i
            WITH nodes[0] AS keep, nodes[i] AS old
            MATCH (old)<-[r:PRODUCES]-(c:Company)
            WHERE NOT (c)-[:PRODUCES]->(keep)
            CREATE (c)-[:PRODUCES]->(keep)
            WITH old, keep
            DETACH DELETE old
            RETURN count(*) AS merged
        """)
        return result.single()['merged'] or 0


def merge_duplicate_materials(driver, dry_run: bool = False) -> int:
    """Merge Material nodes with the same canonical name."""
    if dry_run:
        with driver.session() as session:
            result = session.run("""
                MATCH (m:Material)
                WITH m.name AS name, count(m) AS cnt
                WHERE cnt > 1
                RETURN sum(cnt - 1) AS duplicates
            """)
            duplicates = result.single()['duplicates'] or 0
        print(f"  [DRY RUN] Would merge {duplicates} duplicate material nodes", file=sys.stderr)
        return duplicates
    
    with driver.session() as session:
        result = session.run("""
            MATCH (m:Material)
            WITH m.name AS name, collect(m) AS nodes
            WHERE size(nodes) > 1
            UNWIND range(1, size(nodes)-1) AS i
            WITH nodes[0] AS keep, nodes[i] AS old
            MATCH (old)<-[r:PROCURES]-(c:Company)
            WHERE NOT (c)-[:PROCURES]->(keep)
            CREATE (c)-[:PROCURES]->(keep)
            WITH old, keep
            DETACH DELETE old
            RETURN count(*) AS merged
        """)
        return result.single()['merged'] or 0


def main() -> None:
    parser = argparse.ArgumentParser(description='Apply normalization to Neo4j')
    parser.add_argument('--mapping', required=True, help='Canonical mapping JSON path')
    parser.add_argument('--neo4j-uri', default=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'))
    parser.add_argument('--neo4j-user', default=os.environ.get('NEO4J_USER', 'neo4j'))
    parser.add_argument('--neo4j-password', default=os.environ.get('NEO4J_PASSWORD', 'password'))
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--skip-merge', action='store_true', help='Skip duplicate merging step')
    args = parser.parse_args()
    
    if not os.path.isfile(args.mapping):
        print(f"Mapping file not found: {args.mapping}", file=sys.stderr)
        sys.exit(1)
    
    # Load mapping
    print(f"Loading mapping from {args.mapping}...", file=sys.stderr)
    mapping = load_mapping(args.mapping)
    
    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n", file=sys.stderr)
    
    # Connect to Neo4j
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("Install neo4j: pip install neo4j", file=sys.stderr)
        sys.exit(1)
    
    driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, args.neo4j_password))
    
    # Apply normalizations
    print("\nApplying normalizations...", file=sys.stderr)
    
    # Companies
    company_mapping = mapping.get('company', {}).get('original_to_canonical', {})
    updated_companies = apply_company_normalization(driver, company_mapping, args.dry_run)
    print(f"  Companies: {updated_companies} updated", file=sys.stderr)
    
    # Products
    product_mapping = mapping.get('product', {}).get('original_to_canonical', {})
    updated_products = apply_product_normalization(driver, product_mapping, args.dry_run)
    print(f"  Products: {updated_products} updated", file=sys.stderr)
    
    # Materials
    material_mapping = mapping.get('material', {}).get('original_to_canonical', {})
    updated_materials = apply_material_normalization(driver, material_mapping, args.dry_run)
    print(f"  Materials: {updated_materials} updated", file=sys.stderr)
    
    # Segments
    segment_mapping = mapping.get('segment', {}).get('original_to_canonical', {})
    updated_segments = apply_segment_normalization(driver, segment_mapping, args.dry_run)
    print(f"  Segments: {updated_segments} updated", file=sys.stderr)
    
    # Merge duplicates
    if not args.skip_merge:
        print("\nMerging duplicates...", file=sys.stderr)
        merged_companies = merge_duplicate_companies(driver, args.dry_run)
        merged_products = merge_duplicate_products(driver, args.dry_run)
        merged_materials = merge_duplicate_materials(driver, args.dry_run)
        print(f"  Companies: {merged_companies} merged", file=sys.stderr)
        print(f"  Products: {merged_products} merged", file=sys.stderr)
        print(f"  Materials: {merged_materials} merged", file=sys.stderr)
    
    driver.close()
    
    print("\n✓ Done", file=sys.stderr)


if __name__ == '__main__':
    main()
