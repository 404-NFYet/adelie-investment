"""
Neo4j Service

Neo4j 그래프 데이터베이스 연결 및 쿼리 기능 제공.
공급망 관계 조회에 특화.
"""

from contextlib import contextmanager
from typing import Any, Generator, Optional

from neo4j import GraphDatabase, Driver, Session, Result

from ..core.config import get_settings
from ..core.langsmith_config import with_metadata


class Neo4jService:
    """Neo4j 드라이버 서비스 싱글톤."""
    
    _instance: Optional["Neo4jService"] = None
    _driver: Optional[Driver] = None
    
    def __new__(cls) -> "Neo4jService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._driver is None:
            settings = get_settings()
            self._driver = GraphDatabase.driver(
                settings.neo4j.uri,
                auth=(settings.neo4j.username, settings.neo4j.password),
            )
            self._database = settings.neo4j.database
    
    @property
    def driver(self) -> Driver:
        """Neo4j 드라이버 반환."""
        return self._driver
    
    @property
    def database(self) -> str:
        """기본 데이터베이스명 반환."""
        return self._database
    
    def close(self):
        """드라이버 연결 종료."""
        if self._driver:
            self._driver.close()
            self._driver = None
    
    def verify_connectivity(self) -> bool:
        """연결 상태 확인."""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False


def get_neo4j_service() -> Neo4jService:
    """Neo4j 서비스 인스턴스 반환."""
    return Neo4jService()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Neo4j 세션 컨텍스트 매니저.
    
    Example:
        with get_session() as session:
            result = session.run("MATCH (n) RETURN n LIMIT 10")
    """
    service = get_neo4j_service()
    session = service.driver.session(database=service.database)
    try:
        yield session
    finally:
        session.close()


@with_metadata(run_name="neo4j_query", tags=["neo4j", "query"])
def execute_query(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Cypher 쿼리 실행.
    
    Args:
        query: Cypher 쿼리문
        parameters: 쿼리 파라미터
    
    Returns:
        list[dict]: 쿼리 결과 레코드 목록
    
    Example:
        results = execute_query(
            "MATCH (c:Company {name: $name}) RETURN c",
            {"name": "삼성전자"}
        )
    """
    with get_session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


@with_metadata(run_name="neo4j_query_single", tags=["neo4j", "query"])
def execute_query_single(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """
    단일 결과 반환 쿼리 실행.
    
    Args:
        query: Cypher 쿼리문
        parameters: 쿼리 파라미터
    
    Returns:
        Optional[dict]: 단일 결과 또는 None
    """
    with get_session() as session:
        result = session.run(query, parameters or {})
        record = result.single()
        return record.data() if record else None


@with_metadata(run_name="get_supply_chain", tags=["neo4j", "supply-chain"])
def get_supply_chain(
    company_name: str,
    direction: str = "both",
    depth: int = 2,
) -> dict[str, Any]:
    """
    기업의 공급망 관계 조회.
    
    Args:
        company_name: 기업명
        direction: 조회 방향 (upstream, downstream, both)
        depth: 탐색 깊이 (기본: 2)
    
    Returns:
        dict: 공급망 정보
            - company: 중심 기업 정보
            - suppliers: 공급업체 목록 (upstream)
            - customers: 고객사 목록 (downstream)
            - relationships: 관계 목록
    
    Example:
        supply_chain = get_supply_chain("삼성전자", direction="both", depth=2)
    """
    result = {
        "company": None,
        "suppliers": [],
        "customers": [],
        "relationships": [],
    }
    
    # 중심 기업 조회
    company_query = """
    MATCH (c:Company)
    WHERE c.name = $name OR c.name_en = $name OR c.stock_code = $name
    RETURN c {.*} as company
    LIMIT 1
    """
    company_result = execute_query_single(company_query, {"name": company_name})
    
    if not company_result:
        return result
    
    result["company"] = company_result.get("company")
    
    # 공급업체 (upstream) 조회
    if direction in ("upstream", "both"):
        supplier_query = """
        MATCH path = (supplier:Company)-[r:SUPPLIES*1..$depth]->(c:Company)
        WHERE c.name = $name OR c.name_en = $name OR c.stock_code = $name
        RETURN 
            supplier {.*} as supplier,
            [rel in r | type(rel)] as relationship_types,
            length(path) as distance
        ORDER BY distance
        """
        suppliers = execute_query(
            supplier_query.replace("$depth", str(depth)),
            {"name": company_name}
        )
        result["suppliers"] = suppliers
    
    # 고객사 (downstream) 조회
    if direction in ("downstream", "both"):
        customer_query = """
        MATCH path = (c:Company)-[r:SUPPLIES*1..$depth]->(customer:Company)
        WHERE c.name = $name OR c.name_en = $name OR c.stock_code = $name
        RETURN 
            customer {.*} as customer,
            [rel in r | type(rel)] as relationship_types,
            length(path) as distance
        ORDER BY distance
        """
        customers = execute_query(
            customer_query.replace("$depth", str(depth)),
            {"name": company_name}
        )
        result["customers"] = customers
    
    return result


@with_metadata(run_name="get_company_relationships", tags=["neo4j", "relationships"])
def get_company_relationships(
    company_name: str,
    relationship_types: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """
    기업의 모든 관계 조회.
    
    Args:
        company_name: 기업명
        relationship_types: 조회할 관계 유형 필터 (없으면 전체)
    
    Returns:
        list[dict]: 관계 목록
            - type: 관계 유형
            - direction: 관계 방향 (outgoing, incoming)
            - related_company: 관련 기업 정보
            - properties: 관계 속성
    """
    if relationship_types:
        rel_filter = ":" + "|".join(relationship_types)
    else:
        rel_filter = ""
    
    query = f"""
    MATCH (c:Company)-[r{rel_filter}]-(other:Company)
    WHERE c.name = $name OR c.name_en = $name OR c.stock_code = $name
    RETURN 
        type(r) as type,
        CASE WHEN startNode(r) = c THEN 'outgoing' ELSE 'incoming' END as direction,
        other {{.*}} as related_company,
        properties(r) as properties
    """
    
    return execute_query(query, {"name": company_name})


@with_metadata(run_name="find_path_between_companies", tags=["neo4j", "path"])
def find_path_between_companies(
    company1: str,
    company2: str,
    max_depth: int = 4,
) -> Optional[dict[str, Any]]:
    """
    두 기업 간 최단 경로 조회.
    
    Args:
        company1: 시작 기업명
        company2: 도착 기업명
        max_depth: 최대 탐색 깊이
    
    Returns:
        Optional[dict]: 경로 정보 또는 None
            - path_length: 경로 길이
            - companies: 경로 상의 기업 목록
            - relationships: 경로 상의 관계 목록
    """
    query = """
    MATCH path = shortestPath(
        (c1:Company)-[*1..$depth]-(c2:Company)
    )
    WHERE (c1.name = $company1 OR c1.stock_code = $company1)
      AND (c2.name = $company2 OR c2.stock_code = $company2)
    RETURN 
        length(path) as path_length,
        [node in nodes(path) | node {.*}] as companies,
        [rel in relationships(path) | {type: type(rel), properties: properties(rel)}] as relationships
    LIMIT 1
    """
    
    return execute_query_single(
        query.replace("$depth", str(max_depth)),
        {"company1": company1, "company2": company2}
    )


@with_metadata(run_name="get_industry_companies", tags=["neo4j", "industry"])
def get_industry_companies(
    industry: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    특정 산업의 기업 목록 조회.
    
    Args:
        industry: 산업명 또는 섹터명
        limit: 최대 반환 수
    
    Returns:
        list[dict]: 기업 목록
    """
    query = """
    MATCH (c:Company)-[:BELONGS_TO]->(i:Industry)
    WHERE i.name CONTAINS $industry OR i.sector CONTAINS $industry
    RETURN c {.*} as company, i.name as industry
    ORDER BY c.market_cap DESC
    LIMIT $limit
    """
    
    return execute_query(query, {"industry": industry, "limit": limit})
