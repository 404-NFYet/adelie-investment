"""Neo4j service for company relationship graph."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class Neo4jService:
    """Service for interacting with Neo4j graph database."""
    
    def __init__(self):
        """Initialize Neo4j driver."""
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j package is not installed. Run: pip install neo4j")
        
        self.uri = os.getenv("NEO4J_URI", "bolt://10.10.10.10:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
        )
    
    def close(self):
        """Close the driver connection."""
        self.driver.close()
    
    def verify_connectivity(self) -> bool:
        """Verify connection to Neo4j."""
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            return False
    
    # ==========================================
    # Schema Management
    # ==========================================
    
    def create_constraints(self):
        """Create uniqueness constraints for nodes."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.stock_code IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Material) REQUIRE m.name IS UNIQUE",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"⚠️ Constraint creation issue: {e}")
        
        print("✅ Neo4j constraints created")
    
    def create_indexes(self):
        """Create indexes for efficient queries."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.market)",
            "CREATE INDEX IF NOT EXISTS FOR (s:Sector) ON (s.code)",
            "CREATE INDEX IF NOT EXISTS FOR ()-[r:SUPPLIES]-() ON (r.product)",
        ]
        
        with self.driver.session() as session:
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"⚠️ Index creation issue: {e}")
        
        print("✅ Neo4j indexes created")
    
    def init_schema(self):
        """Initialize Neo4j schema with constraints and indexes."""
        self.create_constraints()
        self.create_indexes()
    
    # ==========================================
    # Company Nodes
    # ==========================================
    
    def create_company(
        self,
        stock_code: str,
        name: str,
        name_en: Optional[str] = None,
        market: str = "KOSPI",
        sector_code: Optional[str] = None,
        sector_name: Optional[str] = None,
    ) -> dict:
        """
        Create or update a company node.
        
        Args:
            stock_code: Stock ticker code
            name: Company name (Korean)
            name_en: Company name (English)
            market: Market (KOSPI/KOSDAQ)
            sector_code: Sector code (KSIC)
            sector_name: Sector name
            
        Returns:
            Created/updated company node
        """
        query = """
        MERGE (c:Company {stock_code: $stock_code})
        SET c.name = $name,
            c.name_en = $name_en,
            c.market = $market,
            c.sector_code = $sector_code,
            c.updated_at = datetime()
        WITH c
        OPTIONAL MATCH (s:Sector {code: $sector_code})
        FOREACH (_ IN CASE WHEN s IS NOT NULL THEN [1] ELSE [] END |
            MERGE (c)-[:BELONGS_TO]->(s)
        )
        FOREACH (_ IN CASE WHEN $sector_name IS NOT NULL AND s IS NULL THEN [1] ELSE [] END |
            MERGE (ns:Sector {name: $sector_name})
            ON CREATE SET ns.code = $sector_code
            MERGE (c)-[:BELONGS_TO]->(ns)
        )
        RETURN c
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                stock_code=stock_code,
                name=name,
                name_en=name_en,
                market=market,
                sector_code=sector_code,
                sector_name=sector_name,
            )
            record = result.single()
            return dict(record["c"]) if record else None
    
    def get_company(self, stock_code: str) -> Optional[dict]:
        """Get a company by stock code."""
        query = """
        MATCH (c:Company {stock_code: $stock_code})
        RETURN c
        """
        
        with self.driver.session() as session:
            result = session.run(query, stock_code=stock_code)
            record = result.single()
            return dict(record["c"]) if record else None
    
    # ==========================================
    # Supply Chain Relationships
    # ==========================================
    
    def create_supply_relationship(
        self,
        supplier_code: str,
        customer_code: str,
        product: str,
        relation_type: str = "SUPPLIES",
        confidence: float = 1.0,
    ) -> bool:
        """
        Create a supply chain relationship between companies.
        
        Args:
            supplier_code: Supplier stock code
            customer_code: Customer stock code
            product: Product/material being supplied
            relation_type: Type of relationship
            confidence: Confidence score
            
        Returns:
            True if created successfully
        """
        query = """
        MATCH (supplier:Company {stock_code: $supplier_code})
        MATCH (customer:Company {stock_code: $customer_code})
        MERGE (supplier)-[r:SUPPLIES {product: $product}]->(customer)
        SET r.confidence = $confidence,
            r.updated_at = datetime()
        RETURN r
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    supplier_code=supplier_code,
                    customer_code=customer_code,
                    product=product,
                    confidence=confidence,
                )
                return result.single() is not None
        except Exception as e:
            print(f"❌ Supply relationship creation failed: {e}")
            return False
    
    def create_competitor_relationship(
        self,
        company1_code: str,
        company2_code: str,
        segment: str,
    ) -> bool:
        """
        Create a competitor relationship between companies.
        
        Args:
            company1_code: First company stock code
            company2_code: Second company stock code
            segment: Market segment where they compete
            
        Returns:
            True if created successfully
        """
        query = """
        MATCH (c1:Company {stock_code: $company1_code})
        MATCH (c2:Company {stock_code: $company2_code})
        MERGE (c1)-[r:COMPETES_WITH {segment: $segment}]->(c2)
        SET r.updated_at = datetime()
        RETURN r
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    company1_code=company1_code,
                    company2_code=company2_code,
                    segment=segment,
                )
                return result.single() is not None
        except Exception as e:
            print(f"❌ Competitor relationship creation failed: {e}")
            return False
    
    # ==========================================
    # Graph Queries
    # ==========================================
    
    def get_supply_chain(
        self,
        stock_code: str,
        direction: str = "both",
        max_hops: int = 2,
    ) -> list[dict]:
        """
        Get supply chain relationships for a company.
        
        Args:
            stock_code: Company stock code
            direction: "suppliers", "customers", or "both"
            max_hops: Maximum relationship hops
            
        Returns:
            List of related companies with relationship info
        """
        if direction == "suppliers":
            query = """
            MATCH (c:Company {stock_code: $stock_code})<-[r:SUPPLIES*1..%d]-(supplier:Company)
            RETURN DISTINCT supplier, r, length(r) as hops
            ORDER BY hops
            """ % max_hops
        elif direction == "customers":
            query = """
            MATCH (c:Company {stock_code: $stock_code})-[r:SUPPLIES*1..%d]->(customer:Company)
            RETURN DISTINCT customer, r, length(r) as hops
            ORDER BY hops
            """ % max_hops
        else:
            query = """
            MATCH (c:Company {stock_code: $stock_code})-[r:SUPPLIES*1..%d]-(related:Company)
            RETURN DISTINCT related, r, length(r) as hops
            ORDER BY hops
            """ % max_hops
        
        results = []
        
        with self.driver.session() as session:
            records = session.run(query, stock_code=stock_code)
            
            for record in records:
                company = dict(record["related"] if "related" in record else 
                              record.get("supplier") or record.get("customer"))
                
                results.append({
                    "company": company,
                    "hops": record["hops"],
                    "relationships": [dict(rel) for rel in record["r"]] if record["r"] else [],
                })
        
        return results
    
    def find_path_between_companies(
        self,
        source_code: str,
        target_code: str,
        max_hops: int = 5,
    ) -> Optional[dict]:
        """
        Find the shortest path between two companies.
        
        Args:
            source_code: Source company stock code
            target_code: Target company stock code
            max_hops: Maximum path length
            
        Returns:
            Path information or None if no path exists
        """
        query = """
        MATCH path = shortestPath(
            (source:Company {stock_code: $source_code})-[*1..%d]-(target:Company {stock_code: $target_code})
        )
        RETURN path, length(path) as length
        """ % max_hops
        
        with self.driver.session() as session:
            result = session.run(
                query,
                source_code=source_code,
                target_code=target_code,
            )
            record = result.single()
            
            if record:
                path = record["path"]
                return {
                    "length": record["length"],
                    "nodes": [dict(node) for node in path.nodes],
                    "relationships": [
                        {
                            "type": rel.type,
                            "properties": dict(rel),
                        }
                        for rel in path.relationships
                    ],
                }
        
        return None
    
    def get_competitors(self, stock_code: str) -> list[dict]:
        """Get competitors of a company."""
        query = """
        MATCH (c:Company {stock_code: $stock_code})-[r:COMPETES_WITH]-(competitor:Company)
        RETURN competitor, r.segment as segment
        """
        
        results = []
        
        with self.driver.session() as session:
            records = session.run(query, stock_code=stock_code)
            
            for record in records:
                results.append({
                    "company": dict(record["competitor"]),
                    "segment": record["segment"],
                })
        
        return results
    
    # ==========================================
    # Bulk Operations
    # ==========================================
    
    def bulk_create_companies(self, companies: list[dict]) -> int:
        """
        Bulk create company nodes.
        
        Args:
            companies: List of company dictionaries
            
        Returns:
            Number of companies created
        """
        query = """
        UNWIND $companies AS comp
        MERGE (c:Company {stock_code: comp.stock_code})
        SET c.name = comp.name,
            c.name_en = comp.name_en,
            c.market = comp.market,
            c.sector_code = comp.sector_code,
            c.updated_at = datetime()
        RETURN count(c) as count
        """
        
        with self.driver.session() as session:
            result = session.run(query, companies=companies)
            record = result.single()
            return record["count"] if record else 0
    
    def bulk_create_relationships(self, relationships: list[dict]) -> int:
        """
        Bulk create supply relationships.
        
        Args:
            relationships: List of relationship dictionaries with
                          supplier_code, customer_code, product, confidence
                          
        Returns:
            Number of relationships created
        """
        query = """
        UNWIND $relationships AS rel
        MATCH (supplier:Company {stock_code: rel.supplier_code})
        MATCH (customer:Company {stock_code: rel.customer_code})
        MERGE (supplier)-[r:SUPPLIES {product: rel.product}]->(customer)
        SET r.confidence = rel.confidence,
            r.updated_at = datetime()
        RETURN count(r) as count
        """
        
        with self.driver.session() as session:
            result = session.run(query, relationships=relationships)
            record = result.single()
            return record["count"] if record else 0
    
    def get_graph_stats(self) -> dict:
        """Get graph database statistics."""
        queries = {
            "companies": "MATCH (c:Company) RETURN count(c) as count",
            "sectors": "MATCH (s:Sector) RETURN count(s) as count",
            "supplies": "MATCH ()-[r:SUPPLIES]->() RETURN count(r) as count",
            "competes": "MATCH ()-[r:COMPETES_WITH]-() RETURN count(r) as count",
        }
        
        stats = {}
        
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query)
                record = result.single()
                stats[key] = record["count"] if record else 0
        
        return stats


# Singleton instance
_neo4j_service: Optional[Neo4jService] = None


def get_neo4j_service() -> Neo4jService:
    """Get Neo4j service instance."""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service


# Test function
def test_neo4j_connection():
    """Test Neo4j connection."""
    try:
        service = get_neo4j_service()
        
        if service.verify_connectivity():
            print("✅ Neo4j connection successful")
            print(f"   URI: {service.uri}")
            
            stats = service.get_graph_stats()
            print(f"   Stats: {stats}")
            
            return True
        else:
            print("❌ Neo4j connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Neo4j connection error: {e}")
        return False


if __name__ == "__main__":
    test_neo4j_connection()
