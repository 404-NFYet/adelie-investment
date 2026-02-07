"""
HybridRAG 검색 서비스

PostgreSQL pgvector (벡터 검색)와 Neo4j (그래프 검색)를 결합한 
하이브리드 RAG 검색 시스템입니다.

Reciprocal Rank Fusion (RRF)을 사용하여 두 검색 결과를 통합합니다.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TypedDict

from app.core.config import get_settings

# TODO: Phase 4에서 sys.path.insert 제거 예정 (패키지 구조 정리 후)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


class SearchResult(TypedDict):
    """검색 결과 타입."""
    id: int
    content: str
    source: str
    score: float
    metadata: dict


class HybridRAGService:
    """
    HybridRAG 검색 서비스.
    
    PostgreSQL pgvector와 Neo4j를 결합하여 다음 검색을 수행합니다:
    1. 벡터 검색 (Semantic Search) - pgvector
    2. 전문 검색 (Full-Text Search) - PostgreSQL tsvector
    3. 그래프 검색 (Graph Search) - Neo4j
    
    Reciprocal Rank Fusion (RRF)으로 결과를 통합합니다.
    """
    
    RRF_K = 60  # RRF 상수 (일반적으로 60 사용)
    
    def __init__(self):
        """서비스 초기화."""
        # OpenAI 클라이언트 (임베딩용)
        self.openai_client = None
        if OPENAI_AVAILABLE:
            api_key = get_settings().OPENAI_API_KEY
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
        
        # PostgreSQL 연결
        self.engine = None
        self.Session = None
        if SQLALCHEMY_AVAILABLE:
            db_url = get_settings().DATABASE_URL
            if db_url:
                # asyncpg를 psycopg2로 변환 (동기 작업용)
                sync_url = db_url.replace("+asyncpg", "").replace("asyncpg://", "postgresql://")
                self.engine = create_engine(sync_url)
                self.Session = sessionmaker(bind=self.engine)
        
        # Neo4j 서비스 (지연 로딩)
        self._neo4j_service = None
    
    @property
    def neo4j_service(self):
        """Neo4j 서비스 지연 로딩."""
        if self._neo4j_service is None:
            try:
                from services.neo4j_service import get_neo4j_service
                self._neo4j_service = get_neo4j_service()
                if not self._neo4j_service.verify_connectivity():
                    self._neo4j_service = None
            except Exception as e:
                print(f"⚠️ Neo4j 연결 실패: {e}")
                self._neo4j_service = None
        return self._neo4j_service
    
    # ==========================================
    # 임베딩 생성
    # ==========================================
    
    def create_embedding(self, text: str) -> list[float]:
        """
        텍스트의 임베딩 벡터 생성.
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            1536차원 임베딩 벡터
        """
        if not self.openai_client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다")
        
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        
        return response.data[0].embedding
    
    # ==========================================
    # 벡터 검색 (pgvector)
    # ==========================================
    
    def vector_search(
        self,
        query: str,
        table: str = "historical_cases",
        embedding_column: str = "embedding",
        content_column: str = "summary",
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        pgvector를 사용한 벡터 유사도 검색.
        
        Args:
            query: 검색 쿼리
            table: 검색할 테이블
            embedding_column: 임베딩 컬럼명
            content_column: 콘텐츠 컬럼명
            limit: 최대 결과 수
            
        Returns:
            유사도 순으로 정렬된 검색 결과
        """
        if not self.Session:
            return []
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.create_embedding(query)
            
            # 임베딩을 PostgreSQL 배열 문자열로 변환
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            # 벡터 검색 쿼리 (pgvector 연산자 사용)
            # psycopg2에서는 %s를 사용해야 하지만, text()에서는 :param 사용
            # ::vector 캐스팅을 위해 직접 쿼리 문자열에 삽입 (안전한 float 배열이므로)
            sql = text(f"""
                SELECT 
                    id,
                    {content_column} as content,
                    1 - ({embedding_column} <=> '{embedding_str}'::vector) as similarity
                FROM {table}
                WHERE {embedding_column} IS NOT NULL
                ORDER BY {embedding_column} <=> '{embedding_str}'::vector
                LIMIT :limit
            """)
            
            with self.Session() as session:
                result = session.execute(sql, {"limit": limit})
                
                results = []
                for row in result:
                    results.append(SearchResult(
                        id=row.id,
                        content=row.content or "",
                        source="vector_search",
                        score=float(row.similarity) if row.similarity else 0.0,
                        metadata={"table": table},
                    ))
                
                return results
                
        except Exception as e:
            print(f"⚠️ 벡터 검색 오류: {e}")
            return []
    
    # ==========================================
    # 전문 검색 (PostgreSQL Full-Text Search)
    # ==========================================
    
    def fulltext_search(
        self,
        query: str,
        table: str = "historical_cases",
        content_column: str = "summary",
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        PostgreSQL 전문 검색.
        
        Args:
            query: 검색 쿼리
            table: 검색할 테이블
            content_column: 검색할 컬럼명
            limit: 최대 결과 수
            
        Returns:
            관련도 순으로 정렬된 검색 결과
        """
        if not self.Session:
            return []
        
        try:
            # 한국어 전문 검색을 위한 LIKE 기반 검색 (Korean isn't natively supported by tsvector)
            # 실제 프로덕션에서는 pg_bigm 또는 별도 FTS 솔루션 사용 권장
            sql = text(f"""
                SELECT 
                    id,
                    {content_column} as content,
                    CASE 
                        WHEN {content_column} ILIKE :exact THEN 1.0
                        WHEN {content_column} ILIKE :start THEN 0.8
                        WHEN {content_column} ILIKE :contains THEN 0.6
                        ELSE 0.4
                    END as relevance
                FROM {table}
                WHERE {content_column} ILIKE :contains
                ORDER BY relevance DESC
                LIMIT :limit
            """)
            
            with self.Session() as session:
                result = session.execute(
                    sql,
                    {
                        "exact": query,
                        "start": f"{query}%",
                        "contains": f"%{query}%",
                        "limit": limit,
                    }
                )
                
                results = []
                for row in result:
                    results.append(SearchResult(
                        id=row.id,
                        content=row.content or "",
                        source="fulltext_search",
                        score=float(row.relevance),
                        metadata={"table": table},
                    ))
                
                return results
                
        except Exception as e:
            print(f"⚠️ 전문 검색 오류: {e}")
            return []
    
    # ==========================================
    # 그래프 검색 (Neo4j)
    # ==========================================
    
    def graph_search(
        self,
        query: str,
        stock_code: Optional[str] = None,
        max_hops: int = 2,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Neo4j 그래프 기반 검색.
        
        회사 관계, 공급망, 경쟁사 등을 그래프 탐색으로 검색합니다.
        
        Args:
            query: 검색 쿼리 (회사명 또는 키워드)
            stock_code: 특정 종목 코드 (선택)
            max_hops: 최대 관계 깊이
            limit: 최대 결과 수
            
        Returns:
            관련 회사 및 관계 정보
        """
        if not self.neo4j_service:
            return []
        
        results = []
        
        try:
            # 종목 코드가 주어진 경우
            if stock_code:
                # 공급망 조회
                supply_chain = self.neo4j_service.get_supply_chain(
                    stock_code=stock_code,
                    direction="both",
                    max_hops=max_hops,
                )
                
                for i, item in enumerate(supply_chain[:limit]):
                    company = item.get("company", {})
                    results.append(SearchResult(
                        id=hash(company.get("stock_code", "")),
                        content=f"{company.get('name', 'Unknown')} ({company.get('stock_code', '')})",
                        source="graph_search",
                        score=1.0 / (item.get("hops", 1) + 1),  # 홉 수에 따른 점수
                        metadata={
                            "stock_code": company.get("stock_code"),
                            "name": company.get("name"),
                            "hops": item.get("hops"),
                            "relationships": item.get("relationships", []),
                        },
                    ))
                
                # 경쟁사 조회
                competitors = self.neo4j_service.get_competitors(stock_code)
                
                for comp in competitors[:limit - len(results)]:
                    company = comp.get("company", {})
                    results.append(SearchResult(
                        id=hash(company.get("stock_code", "")),
                        content=f"{company.get('name', 'Unknown')} (경쟁사)",
                        source="graph_search",
                        score=0.8,
                        metadata={
                            "stock_code": company.get("stock_code"),
                            "name": company.get("name"),
                            "relation": "competitor",
                            "segment": comp.get("segment"),
                        },
                    ))
            
            else:
                # 회사명으로 검색 (Neo4j에서 직접 검색)
                with self.neo4j_service.driver.session() as session:
                    cypher = """
                    MATCH (c:Company)
                    WHERE c.name CONTAINS $query OR c.name_en CONTAINS $query
                    RETURN c
                    LIMIT $limit
                    """
                    
                    records = session.run(cypher, query=query, limit=limit)
                    
                    for record in records:
                        company = dict(record["c"])
                        results.append(SearchResult(
                            id=hash(company.get("stock_code", "")),
                            content=f"{company.get('name', 'Unknown')} ({company.get('stock_code', '')})",
                            source="graph_search",
                            score=0.9,
                            metadata={
                                "stock_code": company.get("stock_code"),
                                "name": company.get("name"),
                                "market": company.get("market"),
                            },
                        ))
        
        except Exception as e:
            print(f"⚠️ 그래프 검색 오류: {e}")
        
        return results
    
    # ==========================================
    # Reciprocal Rank Fusion (RRF)
    # ==========================================
    
    def reciprocal_rank_fusion(
        self,
        result_lists: list[list[SearchResult]],
        k: int = None,
    ) -> list[SearchResult]:
        """
        Reciprocal Rank Fusion으로 여러 검색 결과 통합.
        
        RRF 공식: score(d) = Σ 1 / (k + rank_i(d))
        
        Args:
            result_lists: 여러 검색 엔진의 결과 리스트들
            k: RRF 상수 (기본값: 60)
            
        Returns:
            통합 점수로 재정렬된 결과
        """
        k = k or self.RRF_K
        
        # 문서별 RRF 점수 계산
        doc_scores: dict[int, dict] = {}
        
        for result_list in result_lists:
            for rank, result in enumerate(result_list, start=1):
                doc_id = result["id"]
                rrf_score = 1.0 / (k + rank)
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "result": result,
                        "rrf_score": 0.0,
                        "sources": [],
                    }
                
                doc_scores[doc_id]["rrf_score"] += rrf_score
                doc_scores[doc_id]["sources"].append(result["source"])
        
        # 점수 기준 정렬
        sorted_docs = sorted(
            doc_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )
        
        # 결과 생성
        results = []
        for doc in sorted_docs:
            result = doc["result"].copy()
            result["score"] = doc["rrf_score"]
            result["metadata"]["sources"] = doc["sources"]
            results.append(result)
        
        return results
    
    # ==========================================
    # 하이브리드 검색 (통합)
    # ==========================================
    
    def hybrid_search(
        self,
        query: str,
        table: str = "historical_cases",
        embedding_column: str = "embedding",
        content_column: str = "summary",
        stock_code: Optional[str] = None,
        use_vector: bool = True,
        use_fulltext: bool = True,
        use_graph: bool = True,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        하이브리드 검색 (벡터 + 전문 + 그래프).
        
        세 가지 검색 방법을 결합하여 최적의 결과를 제공합니다.
        
        Args:
            query: 검색 쿼리
            table: 검색할 테이블
            embedding_column: 임베딩 컬럼명
            content_column: 콘텐츠 컬럼명
            stock_code: 특정 종목 코드 (그래프 검색용)
            use_vector: 벡터 검색 사용 여부
            use_fulltext: 전문 검색 사용 여부
            use_graph: 그래프 검색 사용 여부
            limit: 최대 결과 수
            
        Returns:
            RRF로 통합된 검색 결과
        """
        result_lists = []
        
        # 벡터 검색
        if use_vector:
            try:
                vector_results = self.vector_search(
                    query=query,
                    table=table,
                    embedding_column=embedding_column,
                    content_column=content_column,
                    limit=limit * 2,  # 더 많이 가져와서 RRF에서 통합
                )
                if vector_results:
                    result_lists.append(vector_results)
            except Exception as e:
                print(f"⚠️ 벡터 검색 스킵: {e}")
        
        # 전문 검색
        if use_fulltext:
            try:
                fulltext_results = self.fulltext_search(
                    query=query,
                    table=table,
                    content_column=content_column,
                    limit=limit * 2,
                )
                if fulltext_results:
                    result_lists.append(fulltext_results)
            except Exception as e:
                print(f"⚠️ 전문 검색 스킵: {e}")
        
        # 그래프 검색
        if use_graph:
            try:
                graph_results = self.graph_search(
                    query=query,
                    stock_code=stock_code,
                    limit=limit * 2,
                )
                if graph_results:
                    result_lists.append(graph_results)
            except Exception as e:
                print(f"⚠️ 그래프 검색 스킵: {e}")
        
        # 결과가 없으면 빈 리스트 반환
        if not result_lists:
            return []
        
        # 하나의 검색 소스만 있으면 그대로 반환
        if len(result_lists) == 1:
            return result_lists[0][:limit]
        
        # RRF로 통합
        fused_results = self.reciprocal_rank_fusion(result_lists)
        
        return fused_results[:limit]
    
    # ==========================================
    # 고급 검색 기능
    # ==========================================
    
    def search_historical_cases(
        self,
        query: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """
        역사적 사례 검색 (연도 필터 포함).
        
        Args:
            query: 검색 쿼리
            year_from: 시작 연도
            year_to: 종료 연도
            limit: 최대 결과 수
            
        Returns:
            관련 역사적 사례
        """
        results = self.hybrid_search(
            query=query,
            table="historical_cases",
            embedding_column="embedding",
            content_column="summary",
            use_graph=False,  # 역사적 사례는 그래프 검색 제외
            limit=limit * 2,
        )
        
        # 연도 필터 적용 (필요시)
        if year_from or year_to:
            filtered = []
            
            if not self.Session:
                return results[:limit]
            
            with self.Session() as session:
                for result in results:
                    sql = text("""
                        SELECT event_year FROM historical_cases WHERE id = :id
                    """)
                    row = session.execute(sql, {"id": result["id"]}).first()
                    
                    if row and row.event_year:
                        year = row.event_year
                        if year_from and year < year_from:
                            continue
                        if year_to and year > year_to:
                            continue
                        filtered.append(result)
            
            return filtered[:limit]
        
        return results[:limit]
    
    def search_related_companies(
        self,
        stock_code: str,
        relation_type: str = "all",
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        관련 회사 검색.
        
        Args:
            stock_code: 기준 종목 코드
            relation_type: 관계 유형 (supply_chain, competitor, all)
            limit: 최대 결과 수
            
        Returns:
            관련 회사 목록
        """
        results = []
        
        if not self.neo4j_service:
            return results
        
        try:
            if relation_type in ("supply_chain", "all"):
                supply_chain = self.neo4j_service.get_supply_chain(
                    stock_code=stock_code,
                    direction="both",
                    max_hops=2,
                )
                
                for item in supply_chain:
                    company = item.get("company", {})
                    results.append(SearchResult(
                        id=hash(company.get("stock_code", "")),
                        content=company.get("name", "Unknown"),
                        source="supply_chain",
                        score=1.0 / (item.get("hops", 1) + 1),
                        metadata={
                            "stock_code": company.get("stock_code"),
                            "relation_type": "supply_chain",
                            "hops": item.get("hops"),
                        },
                    ))
            
            if relation_type in ("competitor", "all"):
                competitors = self.neo4j_service.get_competitors(stock_code)
                
                for comp in competitors:
                    company = comp.get("company", {})
                    results.append(SearchResult(
                        id=hash(company.get("stock_code", "")),
                        content=company.get("name", "Unknown"),
                        source="competitor",
                        score=0.8,
                        metadata={
                            "stock_code": company.get("stock_code"),
                            "relation_type": "competitor",
                            "segment": comp.get("segment"),
                        },
                    ))
        
        except Exception as e:
            print(f"⚠️ 관련 회사 검색 오류: {e}")
        
        return results[:limit]


# Singleton instance
_hybrid_rag_service: Optional[HybridRAGService] = None


def get_hybrid_rag_service() -> HybridRAGService:
    """HybridRAG 서비스 인스턴스 반환."""
    global _hybrid_rag_service
    if _hybrid_rag_service is None:
        _hybrid_rag_service = HybridRAGService()
    return _hybrid_rag_service


# 테스트 함수
def test_hybrid_rag():
    """HybridRAG 서비스 테스트."""
    print("\n" + "=" * 50)
    print("🧪 HybridRAG 서비스 테스트")
    print("=" * 50)
    
    service = get_hybrid_rag_service()
    
    # 1. 임베딩 테스트
    print("\n1️⃣ 임베딩 생성 테스트...")
    try:
        embedding = service.create_embedding("삼성전자 반도체 사업")
        print(f"   ✅ 임베딩 생성 성공 (차원: {len(embedding)})")
    except Exception as e:
        print(f"   ⚠️ 임베딩 생성 실패: {e}")
    
    # 2. 전문 검색 테스트
    print("\n2️⃣ 전문 검색 테스트...")
    try:
        results = service.fulltext_search("반도체", limit=3)
        print(f"   ✅ 전문 검색 결과: {len(results)}개")
        for r in results[:2]:
            print(f"      - {r['content'][:50]}...")
    except Exception as e:
        print(f"   ⚠️ 전문 검색 실패: {e}")
    
    # 3. 그래프 검색 테스트
    print("\n3️⃣ 그래프 검색 테스트...")
    try:
        results = service.graph_search("삼성전자", stock_code="005930", limit=3)
        print(f"   ✅ 그래프 검색 결과: {len(results)}개")
        for r in results[:2]:
            print(f"      - {r['content']}")
    except Exception as e:
        print(f"   ⚠️ 그래프 검색 실패 (Neo4j 미설치 가능): {e}")
    
    # 4. 하이브리드 검색 테스트
    print("\n4️⃣ 하이브리드 검색 테스트...")
    try:
        results = service.hybrid_search(
            query="반도체 위기",
            use_graph=False,  # Neo4j 없이 테스트
            limit=3,
        )
        print(f"   ✅ 하이브리드 검색 결과: {len(results)}개")
        for r in results[:2]:
            print(f"      - [{r['score']:.3f}] {r['content'][:50]}...")
    except Exception as e:
        print(f"   ⚠️ 하이브리드 검색 실패: {e}")
    
    print("\n" + "=" * 50)
    print("✅ HybridRAG 테스트 완료")
    print("=" * 50)


if __name__ == "__main__":
    test_hybrid_rag()
